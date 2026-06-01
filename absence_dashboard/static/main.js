/* Absence Management Dashboard — main.js */

let dashboardData = null;
let showAll = false; // FR-027: display mode toggle

// ---------------------------------------------------------------------------
// Last-loaded timestamp display  (FR-025)
// ---------------------------------------------------------------------------

function updateLastLoaded(isoStr) {
  const el = document.getElementById("last-loaded");
  if (!el || !isoStr) return;
  // Parse "YYYY-MM-DDTHH:MM:SS" — avoid timezone shifts by constructing locally
  const [datePart, timePart] = isoStr.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hours, minutes] = timePart.split(":");
  const monthName = new Date(year, month - 1, day)
    .toLocaleDateString("en-GB", { month: "short" });
  el.textContent = `Last loaded: ${day} ${monthName} ${year}, ${hours}:${minutes}`;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function apiFetch(url, method = "GET", body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const json = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data: json };
}

// ---------------------------------------------------------------------------
// Warnings banner
// ---------------------------------------------------------------------------

function showWarning(msg, id = null) {
  const container = document.getElementById("warnings");
  const banner = document.createElement("div");
  banner.className = "warning-banner";
  if (id) banner.dataset.warnId = id;
  banner.innerHTML = `<span>${msg}</span><button title="Dismiss">✕</button>`;
  banner.querySelector("button").onclick = () => banner.remove();
  container.appendChild(banner);
}

function clearWarnings() {
  document.getElementById("warnings").innerHTML = "";
}

// ---------------------------------------------------------------------------
// Timeline rendering  (US1 + US2 + US3 + US4)
// Day-level sub-columns within each CW; continuous bar across week boundaries.
// ---------------------------------------------------------------------------

const DAY_ABBR = ["M", "T", "W", "T", "F"];

// Build a flat ordered list of all day-date strings across all weeks.
function buildDayIndex(weeks) {
  const days = [];
  weeks.forEach(cw => cw.days.forEach(d => days.push({ date: d, week: cw.week_number })));
  return days;
}

// For each day in dayIndex, compute the absence CSS class for this member.
// Returns a map: date-string → class string (or "")
function computeDayClasses(mergedBlocks, dayIndex, deadlockWeeks) {
  const absentDates = new Set();
  mergedBlocks.forEach(block => {
    dayIndex.forEach(({ date }) => {
      if (date >= block.start && date <= block.end) absentDates.add(date);
    });
  });

  const deadlockWeekSet = new Set(deadlockWeeks || []);
  const result = {};
  dayIndex.forEach(({ date: d, week }, i) => {
    const prev = i > 0 ? dayIndex[i - 1].date : null;
    const next = i < dayIndex.length - 1 ? dayIndex[i + 1].date : null;
    const absent = absentDates.has(d);

    if (deadlockWeekSet.has(week)) {
      result[d] = "deadlock";
    } else if (absent) {
      const prevAbsent = prev && absentDates.has(prev);
      const nextAbsent = next && absentDates.has(next);
      if (!prevAbsent && !nextAbsent) result[d] = "absent ab-single";
      else if (!prevAbsent)           result[d] = "absent ab-start";
      else if (!nextAbsent)           result[d] = "absent ab-end";
      else                            result[d] = "absent ab-mid";
    } else {
      result[d] = "";
    }
  });
  return result;
}

function renderTimeline(data) {
  const grid = document.getElementById("timeline-grid");
  grid.innerHTML = "";

  if (!data.members || data.members.length === 0) {
    grid.innerHTML = `<div class="empty-state">No project members found — verify the
      "Projekt Migration" column contains "x" values in the Excel file.</div>`;
    return;
  }

  const weeks = data.calendar_weeks;
  const dayIndex = buildDayIndex(weeks);

  // ---- Header row 1: CW labels (each spanning 5 day sub-columns) ----
  const cwHeaderRow = document.createElement("div");
  cwHeaderRow.className = "tg-row tg-header tg-cw-row";
  const nameHeaderCw = document.createElement("div");
  nameHeaderCw.className = "tg-name";
  nameHeaderCw.textContent = "Member";
  cwHeaderRow.appendChild(nameHeaderCw);
  weeks.forEach(cw => {
    const group = document.createElement("div");
    group.className = "tg-cw-group";
    group.title = `${cw.start} – ${cw.end}`;
    group.textContent = cw.label;
    cwHeaderRow.appendChild(group);
  });
  grid.appendChild(cwHeaderRow);

  // ---- Header row 2: day abbreviations (M T W T F repeating) ----
  const dayHeaderRow = document.createElement("div");
  dayHeaderRow.className = "tg-row tg-header tg-day-row";
  const nameHeaderDay = document.createElement("div");
  nameHeaderDay.className = "tg-name";
  dayHeaderRow.appendChild(nameHeaderDay);
  dayIndex.forEach(({ date: d }, i) => {
    const cell = document.createElement("div");
    cell.className = "tg-day-cell tg-day-header";
    cell.textContent = DAY_ABBR[i % 5];
    cell.title = d;
    dayHeaderRow.appendChild(cell);
  });
  grid.appendChild(dayHeaderRow);

  // ---- Phase banner rows (one per phase, overlapping phases stack) ----
  const deadlockWeekSet = new Set(
    data.members.flatMap(m => m.deadlock_weeks || [])
  );

  (data.phases || []).forEach(phase => {
    const row = document.createElement("div");
    row.className = "tg-row tg-phase-row";

    // Mark phase row if any of its days fall in a deadlock CW
    const phaseHasDeadlock = dayIndex.some(
      ({ date: d, week }) =>
        d >= phase.start_date && d <= phase.end_date && deadlockWeekSet.has(week)
    );
    if (phaseHasDeadlock) row.classList.add("phase-has-deadlock");

    const nameCell = document.createElement("div");
    nameCell.className = "tg-name";
    nameCell.textContent = phase.name;
    nameCell.title = `${phase.start_date} – ${phase.end_date}`;
    row.appendChild(nameCell);

    dayIndex.forEach(({ date: d }, i) => {
      const cell = document.createElement("div");
      cell.className = "tg-day-cell";
      if (i % 5 === 0) cell.classList.add("week-start");
      if (d >= phase.start_date && d <= phase.end_date) {
        cell.classList.add("phase-active");
        const isStart = d === phase.start_date || (i % 5 === 0 && d > phase.start_date);
        const isEnd   = d === phase.end_date   || (i % 5 === 4 && d < phase.end_date);
        if (isStart) cell.classList.add("phase-start");
        if (isEnd)   cell.classList.add("phase-end");
        cell.title = `${phase.name}: ${phase.start_date} – ${phase.end_date}`;
      }
      row.appendChild(cell);
    });
    grid.appendChild(row);
  });

  // ---- Member rows ----
  let lastCluster = null;

  data.members.forEach(member => {
    const effectiveCluster = member.clusters.length > 0 ? member.clusters[0] : "Unassigned";

    // Cluster separator row
    if (effectiveCluster !== lastCluster) {
      const sep = document.createElement("div");
      sep.className = "tg-row cluster-sep";
      const sepName = document.createElement("div");
      sepName.className = "tg-name";
      sepName.textContent = effectiveCluster;
      sep.appendChild(sepName);
      grid.appendChild(sep);
      lastCluster = effectiveCluster;
    }

    const row = document.createElement("div");
    row.className = "tg-row";
    if (member.is_bottleneck) row.classList.add("is-bottleneck");

    // FR-027: hide non-migration rows in "Migration Only" mode
    if (!member.is_migration_member) {
      if (!showAll) {
        row.style.display = "none";
      } else {
        row.classList.add("row--non-migration");
      }
    }

    const nameCellEl = document.createElement("div");
    nameCellEl.className = "tg-name";
    nameCellEl.textContent = member.name;
    if (member.is_bottleneck) {
      const badge = document.createElement("span");
      badge.className = "bottleneck-badge";
      badge.textContent = "BN";
      badge.title = "Bottleneck: 2+ dependencies";
      nameCellEl.appendChild(badge);
    }
    row.appendChild(nameCellEl);

    const dayClasses = computeDayClasses(
      member.merged_blocks, dayIndex, member.deadlock_weeks
    );
    const memberDeadlockWeekSet = new Set(member.deadlock_weeks || []);

    dayIndex.forEach(({ date: d, week }, i) => {
      const cell = document.createElement("div");
      cell.className = "tg-day-cell";
      const cls = dayClasses[d];
      if (cls) cls.split(" ").forEach(c => cell.classList.add(c));

      if (i % 5 === 0) cell.classList.add("week-start");

      if (cls === "deadlock") {
        cell.title = `Deadlock CW${week}: all pool members absent`;
        if (i % 5 === 0) {
          const label = document.createElement("span");
          label.className = "deadlock-label";
          label.textContent = "Deadlock";
          cell.appendChild(label);
        }
      } else {
        cell.title = d;
      }

      row.appendChild(cell);
    });

    grid.appendChild(row);
  });

  // ---- Today indicator  (FR-026) ----
  applyTodayIndicator(dayIndex, grid);
}

// ---------------------------------------------------------------------------
// Today indicator  (FR-026)
// ---------------------------------------------------------------------------

function applyTodayIndicator(dayIndex, grid) {
  const now = new Date();
  const dayOfWeek = now.getDay(); // 0 = Sun, 6 = Sat
  if (dayOfWeek === 0 || dayOfWeek === 6) return;

  // Build YYYY-MM-DD without timezone drift
  const todayISO = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");

  const todayColIndex = dayIndex.findIndex(({ date }) => date === todayISO);
  if (todayColIndex === -1) return; // today outside visible range

  Array.from(grid.children).forEach(row => {
    // Skip CW group header row (cells are week-wide, not day-wide)
    if (row.classList.contains("tg-cw-row")) return;
    // Skip cluster separator rows (no day cells)
    if (row.classList.contains("cluster-sep")) return;

    const col = row.children[todayColIndex + 1]; // +1 for the sticky name column
    if (!col) return;
    col.classList.add("today-col-start");

    // Insert "Today" label in the day-abbreviation header row
    if (row.classList.contains("tg-day-row")) {
      const label = document.createElement("span");
      label.className = "today-label";
      label.textContent = "Today";
      col.prepend(label);
    }
  });
}

// ---------------------------------------------------------------------------
// Inline edit helpers
// ---------------------------------------------------------------------------

function makeSelect(names, selectedValue, cls) {
  const sel = document.createElement("select");
  if (cls) sel.className = cls;
  names.forEach(n => {
    const opt = document.createElement("option");
    opt.value = opt.textContent = n;
    if (n === selectedValue) opt.selected = true;
    sel.appendChild(opt);
  });
  return sel;
}

function showInlineError(container, msg) {
  let errEl = container.querySelector(".inline-edit-error");
  if (!errEl) {
    errEl = document.createElement("div");
    errEl.className = "inline-edit-error";
    container.appendChild(errEl);
  }
  errEl.textContent = msg;
}

function clearInlineError(container) {
  const errEl = container.querySelector(".inline-edit-error");
  if (errEl) errEl.remove();
}

// ---------------------------------------------------------------------------
// Dependency panel  (US2 + Phase 11 inline edit)
// ---------------------------------------------------------------------------

function renderDependencies(data) {
  const fromSel = document.getElementById("dep-from");
  const toSel   = document.getElementById("dep-to");
  const list    = document.getElementById("dep-list");
  // FR-027: management panels always scoped to migration members only
  const names   = data.members.filter(m => m.is_migration_member).map(m => m.name).sort();

  // Refresh "from" single-select
  const currentFrom = fromSel.value;
  fromSel.innerHTML = `<option value="">— select —</option>`;
  names.forEach(n => {
    const opt = document.createElement("option");
    opt.value = opt.textContent = n;
    if (n === currentFrom) opt.selected = true;
    fromSel.appendChild(opt);
  });

  // Refresh "to" multi-select (preserve current selections)
  const currentTo = new Set(
    Array.from(toSel.selectedOptions).map(o => o.value)
  );
  toSel.innerHTML = "";
  names.forEach(n => {
    const opt = document.createElement("option");
    opt.value = opt.textContent = n;
    if (currentTo.has(n)) opt.selected = true;
    toSel.appendChild(opt);
  });

  list.innerHTML = "";
  data.dependencies.forEach(dep => {
    const li = document.createElement("li");
    const toLabel = (dep.to_members || []).join(", ");

    // --- display view ---
    const displayDiv = document.createElement("div");
    displayDiv.className = "item-display";
    const rangeText = dep.active_from
      ? ` (${dep.active_from} – ${dep.active_to})`
      : "";
    displayDiv.innerHTML =
      `<span>${dep.from_member} → ${toLabel}<span class="cluster-item-members">${rangeText}</span></span>`;

    const editBtn = document.createElement("button");
    editBtn.className = "btn-edit";
    editBtn.textContent = "Edit";
    editBtn.title = "Edit dependency";

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "✕";
    removeBtn.title = "Remove dependency";
    removeBtn.onclick = async () => {
      const body = { from_member: dep.from_member, to_members: dep.to_members };
      if (dep.active_from) { body.active_from = dep.active_from; body.active_to = dep.active_to; }
      const res = await apiFetch("/api/dependencies", "DELETE", body);
      if (res.ok) { await refreshDashboard(); } else {
        showWarning(`Could not remove dependency: ${res.data.error}`);
      }
    };
    displayDiv.appendChild(editBtn);
    displayDiv.appendChild(removeBtn);

    // --- edit view ---
    const editDiv = document.createElement("div");
    editDiv.className = "item-edit hidden";

    const newFromSel = makeSelect(names, dep.from_member, "edit-select");
    const arrow = document.createElement("span");
    arrow.textContent = " → ";

    const newToSel = document.createElement("select");
    newToSel.multiple = true;
    newToSel.className = "edit-select-multi";
    names.forEach(n => {
      const opt = document.createElement("option");
      opt.value = opt.textContent = n;
      if ((dep.to_members || []).includes(n)) opt.selected = true;
      newToSel.appendChild(opt);
    });

    const newActiveFrom = document.createElement("input");
    newActiveFrom.type = "date";
    newActiveFrom.className = "edit-input";
    newActiveFrom.value = dep.active_from || "";
    newActiveFrom.title = "Active from (optional)";

    const dash = document.createElement("span");
    dash.textContent = " – ";

    const newActiveTo = document.createElement("input");
    newActiveTo.type = "date";
    newActiveTo.className = "edit-input";
    newActiveTo.value = dep.active_to || "";
    newActiveTo.title = "Active to (optional)";

    const saveBtn = document.createElement("button");
    saveBtn.className = "btn-save";
    saveBtn.textContent = "Save";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-cancel";
    cancelBtn.textContent = "Cancel";

    editDiv.append(newFromSel, arrow, newToSel, newActiveFrom, dash, newActiveTo, saveBtn, cancelBtn);

    editBtn.onclick = () => {
      displayDiv.classList.add("hidden");
      editDiv.classList.remove("hidden");
    };
    cancelBtn.onclick = () => {
      clearInlineError(editDiv);
      Array.from(newToSel.options).forEach(o => {
        o.selected = (dep.to_members || []).includes(o.value);
      });
      displayDiv.classList.remove("hidden");
      editDiv.classList.add("hidden");
    };
    saveBtn.onclick = async () => {
      clearInlineError(editDiv);
      const newToMembers = Array.from(newToSel.selectedOptions).map(o => o.value);
      const body = {
        old_from: dep.from_member,
        old_to_members: dep.to_members,
        old_active_from: dep.active_from || null,
        old_active_to: dep.active_to || null,
        new_from: newFromSel.value,
        new_to_members: newToMembers,
        new_active_from: newActiveFrom.value || null,
        new_active_to: newActiveTo.value || null,
      };
      const res = await apiFetch("/api/dependencies", "PUT", body);
      if (res.ok) {
        await refreshDashboard();
      } else {
        showInlineError(editDiv, res.data.error || "Could not save dependency.");
      }
    };

    li.appendChild(displayDiv);
    li.appendChild(editDiv);
    list.appendChild(li);
  });
}

document.getElementById("btn-add-dep").addEventListener("click", async () => {
  const from       = document.getElementById("dep-from").value;
  const toMembers  = Array.from(
    document.getElementById("dep-to").selectedOptions
  ).map(o => o.value);
  const activeFrom = document.getElementById("dep-active-from").value || null;
  const activeTo   = document.getElementById("dep-active-to").value || null;
  const errEl = document.getElementById("dep-error");
  errEl.classList.add("hidden");
  if (!from || toMembers.length === 0) return;
  const body = { from_member: from, to_members: toMembers };
  if (activeFrom) { body.active_from = activeFrom; body.active_to = activeTo; }
  const res = await apiFetch("/api/dependencies", "POST", body);
  if (res.ok) {
    document.getElementById("dep-active-from").value = "";
    document.getElementById("dep-active-to").value = "";
    await refreshDashboard();
  } else {
    errEl.textContent = res.data.error || "Could not add dependency.";
    errEl.classList.remove("hidden");
  }
});

// ---------------------------------------------------------------------------
// Cluster panel  (US4 + Phase 11 inline edit)
// ---------------------------------------------------------------------------

function renderClusters(data) {
  const membersSelect = document.getElementById("cluster-members");
  const list          = document.getElementById("cluster-list");
  // FR-027: management panels always scoped to migration members only
  const names         = data.members.filter(m => m.is_migration_member).map(m => m.name).sort();

  const selectedValues = Array.from(membersSelect.selectedOptions).map(o => o.value);
  membersSelect.innerHTML = "";
  names.forEach(n => {
    const opt = document.createElement("option");
    opt.value = opt.textContent = n;
    if (selectedValues.includes(n)) opt.selected = true;
    membersSelect.appendChild(opt);
  });

  list.innerHTML = "";
  data.skill_clusters.forEach(cluster => {
    const li = document.createElement("li");

    // --- display view ---
    const displayDiv = document.createElement("div");
    displayDiv.className = "item-display";
    displayDiv.innerHTML = `<span><strong>${cluster.name}</strong> <span class="cluster-item-members">${cluster.members.join(", ") || "(empty)"}</span></span>`;

    const editBtn = document.createElement("button");
    editBtn.className = "btn-edit";
    editBtn.textContent = "Edit";
    editBtn.title = "Edit cluster";

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "✕";
    removeBtn.title = "Delete cluster";
    removeBtn.onclick = async () => {
      const res = await apiFetch(`/api/clusters/${encodeURIComponent(cluster.name)}`, "DELETE");
      if (res.ok) { await refreshDashboard(); } else {
        showWarning(`Could not delete cluster: ${res.data.error}`);
      }
    };
    displayDiv.appendChild(editBtn);
    displayDiv.appendChild(removeBtn);

    // --- edit view ---
    const editDiv = document.createElement("div");
    editDiv.className = "item-edit hidden";

    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.className = "edit-input";
    nameInput.value = cluster.name;
    nameInput.placeholder = "Cluster name";

    const membersMulti = document.createElement("select");
    membersMulti.multiple = true;
    membersMulti.className = "edit-select-multi";
    names.forEach(n => {
      const opt = document.createElement("option");
      opt.value = opt.textContent = n;
      if (cluster.members.includes(n)) opt.selected = true;
      membersMulti.appendChild(opt);
    });

    const saveBtn = document.createElement("button");
    saveBtn.className = "btn-save";
    saveBtn.textContent = "Save";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-cancel";
    cancelBtn.textContent = "Cancel";

    editDiv.append(nameInput, membersMulti, saveBtn, cancelBtn);

    editBtn.onclick = () => {
      displayDiv.classList.add("hidden");
      editDiv.classList.remove("hidden");
    };
    cancelBtn.onclick = () => {
      clearInlineError(editDiv);
      nameInput.value = cluster.name;
      Array.from(membersMulti.options).forEach(o => {
        o.selected = cluster.members.includes(o.value);
      });
      displayDiv.classList.remove("hidden");
      editDiv.classList.add("hidden");
    };
    saveBtn.onclick = async () => {
      clearInlineError(editDiv);
      const newName = nameInput.value.trim();
      const newMembers = Array.from(membersMulti.selectedOptions).map(o => o.value);
      const body = { name: newName, members: newMembers };
      const res = await apiFetch(
        `/api/clusters/${encodeURIComponent(cluster.name)}`, "PUT", body
      );
      if (res.ok) {
        await refreshDashboard();
      } else {
        showInlineError(editDiv, res.data.error || "Could not save cluster.");
      }
    };

    li.appendChild(displayDiv);
    li.appendChild(editDiv);
    list.appendChild(li);
  });
}

document.getElementById("btn-create-cluster").addEventListener("click", async () => {
  const name = document.getElementById("cluster-name").value.trim();
  const members = Array.from(
    document.getElementById("cluster-members").selectedOptions
  ).map(o => o.value);
  const errEl = document.getElementById("cluster-error");
  errEl.classList.add("hidden");
  if (!name) return;
  const res = await apiFetch("/api/clusters", "POST", { name, members });
  if (res.ok) {
    document.getElementById("cluster-name").value = "";
    await refreshDashboard();
  } else {
    errEl.textContent = res.data.error || "Could not create cluster.";
    errEl.classList.remove("hidden");
  }
});

// ---------------------------------------------------------------------------
// Phase panel  (US6 + Phase 11 inline edit)
// ---------------------------------------------------------------------------

function renderPhases(data) {
  const list = document.getElementById("phase-list");
  list.innerHTML = "";
  (data.phases || []).forEach(phase => {
    const li = document.createElement("li");

    // --- display view ---
    const displayDiv = document.createElement("div");
    displayDiv.className = "item-display";
    displayDiv.innerHTML = `<span><strong>${phase.name}</strong> <span class="cluster-item-members">${phase.start_date} – ${phase.end_date}</span></span>`;

    const editBtn = document.createElement("button");
    editBtn.className = "btn-edit";
    editBtn.textContent = "Edit";
    editBtn.title = "Edit phase";

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "✕";
    removeBtn.title = "Remove phase";
    removeBtn.onclick = async () => {
      const res = await apiFetch(`/api/phases/${encodeURIComponent(phase.name)}`, "DELETE");
      if (res.ok) { await refreshDashboard(); } else {
        showWarning(`Could not remove phase: ${res.data.error}`);
      }
    };
    displayDiv.appendChild(editBtn);
    displayDiv.appendChild(removeBtn);

    // --- edit view ---
    const editDiv = document.createElement("div");
    editDiv.className = "item-edit hidden";

    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.className = "edit-input";
    nameInput.value = phase.name;
    nameInput.placeholder = "Phase name";

    const startInput = document.createElement("input");
    startInput.type = "date";
    startInput.className = "edit-input";
    startInput.value = phase.start_date;

    const endInput = document.createElement("input");
    endInput.type = "date";
    endInput.className = "edit-input";
    endInput.value = phase.end_date;

    const saveBtn = document.createElement("button");
    saveBtn.className = "btn-save";
    saveBtn.textContent = "Save";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-cancel";
    cancelBtn.textContent = "Cancel";

    editDiv.append(nameInput, startInput, endInput, saveBtn, cancelBtn);

    editBtn.onclick = () => {
      displayDiv.classList.add("hidden");
      editDiv.classList.remove("hidden");
    };
    cancelBtn.onclick = () => {
      clearInlineError(editDiv);
      nameInput.value = phase.name;
      startInput.value = phase.start_date;
      endInput.value = phase.end_date;
      displayDiv.classList.remove("hidden");
      editDiv.classList.add("hidden");
    };
    saveBtn.onclick = async () => {
      clearInlineError(editDiv);
      const body = {
        name: nameInput.value.trim(),
        start_date: startInput.value,
        end_date: endInput.value,
      };
      const res = await apiFetch(
        `/api/phases/${encodeURIComponent(phase.name)}`, "PUT", body
      );
      if (res.ok) {
        await refreshDashboard();
      } else {
        showInlineError(editDiv, res.data.error || "Could not save phase.");
      }
    };

    li.appendChild(displayDiv);
    li.appendChild(editDiv);
    list.appendChild(li);
  });
}

document.getElementById("btn-add-phase").addEventListener("click", async () => {
  const name  = document.getElementById("phase-name").value.trim();
  const start = document.getElementById("phase-start").value;
  const end   = document.getElementById("phase-end").value;
  const errEl = document.getElementById("phase-error");
  errEl.classList.add("hidden");
  if (!name || !start || !end) return;
  const res = await apiFetch("/api/phases", "POST",
    { name, start_date: start, end_date: end });
  if (res.ok) {
    document.getElementById("phase-name").value = "";
    document.getElementById("phase-start").value = "";
    document.getElementById("phase-end").value = "";
    await refreshDashboard();
  } else {
    errEl.textContent = res.data.error || "Could not add phase.";
    errEl.classList.remove("hidden");
  }
});

// ---------------------------------------------------------------------------
// Display mode toggle  (FR-027)
// ---------------------------------------------------------------------------

document.getElementById("btn-toggle-filter").addEventListener("click", () => {
  showAll = !showAll;
  const btn = document.getElementById("btn-toggle-filter");
  btn.textContent = showAll ? "Show All" : "Migration Only";
  btn.classList.toggle("active", showAll);
  if (dashboardData) renderTimeline(dashboardData);
});

// ---------------------------------------------------------------------------
// Panel toggles
// ---------------------------------------------------------------------------

document.getElementById("btn-toggle-phases").addEventListener("click", () => {
  document.getElementById("phase-panel").classList.toggle("hidden");
});
document.getElementById("btn-toggle-deps").addEventListener("click", () => {
  document.getElementById("dependency-panel").classList.toggle("hidden");
});
document.getElementById("btn-toggle-clusters").addEventListener("click", () => {
  document.getElementById("cluster-panel").classList.toggle("hidden");
});

// ---------------------------------------------------------------------------
// Reload / refresh  (US5)
// ---------------------------------------------------------------------------

document.getElementById("btn-reload").addEventListener("click", async () => {
  const btn = document.getElementById("btn-reload");
  btn.disabled = true;
  btn.textContent = "⟳ Reloading…";
  try {
    const res = await apiFetch("/api/refresh", "POST");
    if (res.ok) {
      dashboardData = res.data;
      updateLastLoaded(dashboardData.last_loaded);
      renderTimeline(dashboardData);
      renderDependencies(dashboardData);
      renderClusters(dashboardData);
      renderPhases(dashboardData);
      clearWarnings();
      if (dashboardData.removed_stale_references &&
          dashboardData.removed_stale_references.length > 0) {
        showWarning(
          `${dashboardData.removed_stale_references.length} stale reference(s) removed ` +
          `after reload (members no longer in Excel).`
        );
      }
      if (dashboardData.skipped_rows && dashboardData.skipped_rows.length > 0) {
        showWarning(
          `${dashboardData.skipped_rows.length} row(s) skipped due to empty name.`
        );
      }
    } else {
      showWarning("Could not reload Excel file — showing last loaded data.");
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "⟳ Reload";
  }
});

// ---------------------------------------------------------------------------
// Initial load
// ---------------------------------------------------------------------------

async function refreshDashboard() {
  const res = await apiFetch("/api/dashboard");
  if (!res.ok) {
    showWarning("Failed to load dashboard data.");
    return;
  }
  dashboardData = res.data;
  updateLastLoaded(dashboardData.last_loaded);
  renderTimeline(dashboardData);
  renderDependencies(dashboardData);
  renderClusters(dashboardData);
  renderPhases(dashboardData);
  if (dashboardData.skipped_rows && dashboardData.skipped_rows.length > 0) {
    showWarning(
      `${dashboardData.skipped_rows.length} row(s) skipped due to empty name in Column D.`
    );
  }
}

refreshDashboard();
