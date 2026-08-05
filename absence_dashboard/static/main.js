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

// Groups a member's cumul_risks (or sole_coverage) entries by week_number.
// Returns a Map: week_number → [group name, ...]
function groupByWeek(entries) {
  const map = new Map();
  (entries || []).forEach(({ group, week_number }) => {
    if (!map.has(week_number)) map.set(week_number, []);
    map.get(week_number).push(group);
  });
  return map;
}

// For each day in dayIndex, compute the absence CSS class for this member.
// Returns a map: date-string → class string (or "")
function computeDayClasses(mergedBlocks, dayIndex, cumulRiskWeekMap) {
  const absentDates = new Set();
  mergedBlocks.forEach(block => {
    dayIndex.forEach(({ date }) => {
      if (date >= block.start && date <= block.end) absentDates.add(date);
    });
  });

  const result = {};
  dayIndex.forEach(({ date: d, week }, i) => {
    const prev = i > 0 ? dayIndex[i - 1].date : null;
    const next = i < dayIndex.length - 1 ? dayIndex[i + 1].date : null;
    const absent = absentDates.has(d);

    if (absent && cumulRiskWeekMap.has(week)) {
      result[d] = "cumul-risk";
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
  const cumulRiskWeekSet = new Set(
    data.members.flatMap(m => (m.cumul_risks || []).map(r => r.week_number))
  );

  (data.phases || []).forEach(phase => {
    const row = document.createElement("div");
    row.className = "tg-row tg-phase-row";

    // Mark phase row if any of its days fall in a cumul-risk CW
    const phaseHasCumulRisk = dayIndex.some(
      ({ date: d, week }) =>
        d >= phase.start_date && d <= phase.end_date && cumulRiskWeekSet.has(week)
    );
    if (phaseHasCumulRisk) row.classList.add("phase-has-cumul-risk");

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

    // FR-027: hide non-migration rows in "Migration Only" mode
    if (!member.is_migration_member) {
      if (!showAll) {
        row.style.display = "none";
      } else {
        row.classList.add("row--non-migration");
      }
    }

    const soleCoverageWeekMap = groupByWeek(member.sole_coverage);
    if (soleCoverageWeekMap.size > 0) row.classList.add("is-sole-coverage");

    const nameCellEl = document.createElement("div");
    nameCellEl.className = "tg-name";
    nameCellEl.textContent = member.name;
    const soleGroups = [...new Set((member.sole_coverage || []).map(r => r.group))];
    soleGroups.forEach(groupName => {
      const weeks = (member.sole_coverage || [])
        .filter(r => r.group === groupName)
        .map(r => r.week_number);
      const badge = document.createElement("span");
      badge.className = "sole-coverage-badge";
      badge.textContent = "Sole";
      badge.title = `Sole coverage for "${groupName}": CW${weeks.join(", CW")}`;
      nameCellEl.appendChild(badge);
    });
    row.appendChild(nameCellEl);

    const cumulRiskWeekMap = groupByWeek(member.cumul_risks);
    const dayClasses = computeDayClasses(member.merged_blocks, dayIndex, cumulRiskWeekMap);
    const labeledWeeks = new Set();

    dayIndex.forEach(({ date: d, week }, i) => {
      const cell = document.createElement("div");
      cell.className = "tg-day-cell";
      const cls = dayClasses[d];
      if (cls) cls.split(" ").forEach(c => cell.classList.add(c));

      if (i % 5 === 0) cell.classList.add("week-start");

      if (cls === "cumul-risk") {
        const groups = cumulRiskWeekMap.get(week) || [];
        cell.title = `Cumul risk CW${week}: ${groups.join(", ")}`;
        if (!labeledWeeks.has(week)) {
          labeledWeeks.add(week);
          const label = document.createElement("span");
          label.className = "cumul-risk-label";
          label.textContent = "Cumul risk";
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
// Cumul group panel  (US1 + US2)
// ---------------------------------------------------------------------------

function renderCumulGroups(data) {
  const membersSelect = document.getElementById("cumul-members");
  const list          = document.getElementById("cumul-list");
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
  (data.cumul_groups || []).forEach(group => {
    const li = document.createElement("li");

    // --- display view ---
    const displayDiv = document.createElement("div");
    displayDiv.className = "item-display";
    const activeRange = group.active_from
      ? ` <span class="cluster-item-members">(${group.active_from} – ${group.active_to})</span>`
      : "";
    displayDiv.innerHTML = `<span><strong>${group.name}</strong> <span class="cluster-item-members">${group.members.join(", ")}</span>${activeRange}</span>`;

    const editBtn = document.createElement("button");
    editBtn.className = "btn-edit";
    editBtn.textContent = "Edit";
    editBtn.title = "Edit cumul group";

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "✕";
    removeBtn.title = "Delete cumul group";
    removeBtn.onclick = async () => {
      const res = await apiFetch(`/api/cumul-groups/${encodeURIComponent(group.name)}`, "DELETE");
      if (res.ok) { await refreshDashboard(); } else {
        showWarning(`Could not delete cumul group: ${res.data.error}`);
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
    nameInput.value = group.name;
    nameInput.placeholder = "Group name";

    const membersMulti = document.createElement("select");
    membersMulti.multiple = true;
    membersMulti.className = "edit-select-multi";
    names.forEach(n => {
      const opt = document.createElement("option");
      opt.value = opt.textContent = n;
      if (group.members.includes(n)) opt.selected = true;
      membersMulti.appendChild(opt);
    });

    const activeFromInput = document.createElement("input");
    activeFromInput.type = "date";
    activeFromInput.className = "edit-input";
    activeFromInput.value = group.active_from || "";

    const activeToInput = document.createElement("input");
    activeToInput.type = "date";
    activeToInput.className = "edit-input";
    activeToInput.value = group.active_to || "";

    const saveBtn = document.createElement("button");
    saveBtn.className = "btn-save";
    saveBtn.textContent = "Save";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-cancel";
    cancelBtn.textContent = "Cancel";

    editDiv.append(nameInput, membersMulti, activeFromInput, activeToInput, saveBtn, cancelBtn);

    editBtn.onclick = () => {
      displayDiv.classList.add("hidden");
      editDiv.classList.remove("hidden");
    };
    cancelBtn.onclick = () => {
      clearInlineError(editDiv);
      nameInput.value = group.name;
      Array.from(membersMulti.options).forEach(o => {
        o.selected = group.members.includes(o.value);
      });
      activeFromInput.value = group.active_from || "";
      activeToInput.value = group.active_to || "";
      displayDiv.classList.remove("hidden");
      editDiv.classList.add("hidden");
    };
    saveBtn.onclick = async () => {
      clearInlineError(editDiv);
      const newName = nameInput.value.trim();
      const newMembers = Array.from(membersMulti.selectedOptions).map(o => o.value);
      const body = {
        name: newName,
        members: newMembers,
        active_from: activeFromInput.value || null,
        active_to: activeToInput.value || null,
      };
      const res = await apiFetch(
        `/api/cumul-groups/${encodeURIComponent(group.name)}`, "PUT", body
      );
      if (res.ok) {
        await refreshDashboard();
      } else {
        showInlineError(editDiv, res.data.error || "Could not save cumul group.");
      }
    };

    li.appendChild(displayDiv);
    li.appendChild(editDiv);
    list.appendChild(li);
  });
}

document.getElementById("btn-add-cumul").addEventListener("click", async () => {
  const name = document.getElementById("cumul-name").value.trim();
  const members = Array.from(
    document.getElementById("cumul-members").selectedOptions
  ).map(o => o.value);
  const activeFrom = document.getElementById("cumul-active-from").value;
  const activeTo = document.getElementById("cumul-active-to").value;
  const errEl = document.getElementById("cumul-error");
  errEl.classList.add("hidden");
  if (!name) return;
  const body = { name, members };
  if (activeFrom || activeTo) {
    body.active_from = activeFrom || null;
    body.active_to = activeTo || null;
  }
  const res = await apiFetch("/api/cumul-groups", "POST", body);
  if (res.ok) {
    document.getElementById("cumul-name").value = "";
    document.getElementById("cumul-active-from").value = "";
    document.getElementById("cumul-active-to").value = "";
    await refreshDashboard();
  } else {
    errEl.textContent = res.data.error || "Could not create cumul group.";
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
document.getElementById("btn-toggle-cumul").addEventListener("click", () => {
  document.getElementById("cumul-panel").classList.toggle("hidden");
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
      renderCumulGroups(dashboardData);
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
  renderCumulGroups(dashboardData);
  renderClusters(dashboardData);
  renderPhases(dashboardData);
  if (dashboardData.skipped_rows && dashboardData.skipped_rows.length > 0) {
    showWarning(
      `${dashboardData.skipped_rows.length} row(s) skipped due to empty name in Column D.`
    );
  }
}

refreshDashboard();
