/* Absence Management Dashboard — main.js */

let dashboardData = null;

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
function computeDayClasses(mergedBlocks, dayIndex, isBottleneck, atRiskWeeks) {
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
    const atRisk = atRiskWeeks.includes(week);

    if (absent) {
      const prevAbsent = prev && absentDates.has(prev);
      const nextAbsent = next && absentDates.has(next);
      if (isBottleneck) {
        if (!prevAbsent && !nextAbsent) result[d] = "bottleneck-absent ba-single";
        else if (!prevAbsent)           result[d] = "bottleneck-absent ba-start";
        else if (!nextAbsent)           result[d] = "bottleneck-absent ba-end";
        else                            result[d] = "bottleneck-absent ba-mid";
      } else {
        if (!prevAbsent && !nextAbsent) result[d] = "absent ab-single";
        else if (!prevAbsent)           result[d] = "absent ab-start";
        else if (!nextAbsent)           result[d] = "absent ab-end";
        else                            result[d] = "absent ab-mid";
      }
    } else if (atRisk) {
      result[d] = "at-risk";
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
  (data.phases || []).forEach(phase => {
    const row = document.createElement("div");
    row.className = "tg-row tg-phase-row";

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
      member.merged_blocks, dayIndex, member.is_bottleneck, member.at_risk_weeks
    );

    dayIndex.forEach(({ date: d, week }, i) => {
      const cell = document.createElement("div");
      cell.className = "tg-day-cell";
      const cls = dayClasses[d];
      if (cls) cls.split(" ").forEach(c => cell.classList.add(c));

      // Week-boundary separator (first day of a week gets a left border marker)
      if (i % 5 === 0) cell.classList.add("week-start");

      if (cls.includes("absent") || cls.includes("bottleneck-absent")) {
        cell.title = d;
      } else if (cls === "at-risk") {
        cell.title = `At risk CW${week}: depends on ${member.depends_on.join(", ")}`;
      } else {
        cell.title = d;
      }

      row.appendChild(cell);
    });

    grid.appendChild(row);
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
  const names   = data.members.map(m => m.name).sort();

  [fromSel, toSel].forEach(sel => {
    const current = sel.value;
    sel.innerHTML = `<option value="">— select —</option>`;
    names.forEach(n => {
      const opt = document.createElement("option");
      opt.value = opt.textContent = n;
      if (n === current) opt.selected = true;
      sel.appendChild(opt);
    });
  });

  list.innerHTML = "";
  data.dependencies.forEach(dep => {
    const li = document.createElement("li");

    // --- display view ---
    const displayDiv = document.createElement("div");
    displayDiv.className = "item-display";
    displayDiv.innerHTML = `<span>${dep.from_member} → ${dep.to_member}</span>`;

    const editBtn = document.createElement("button");
    editBtn.className = "btn-edit";
    editBtn.textContent = "Edit";
    editBtn.title = "Edit dependency";

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "✕";
    removeBtn.title = "Remove dependency";
    removeBtn.onclick = async () => {
      const res = await apiFetch("/api/dependencies", "DELETE",
        { from_member: dep.from_member, to_member: dep.to_member });
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
    const newToSel = makeSelect(names, dep.to_member, "edit-select");

    const saveBtn = document.createElement("button");
    saveBtn.className = "btn-save";
    saveBtn.textContent = "Save";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-cancel";
    cancelBtn.textContent = "Cancel";

    editDiv.append(newFromSel, arrow, newToSel, saveBtn, cancelBtn);

    editBtn.onclick = () => {
      displayDiv.classList.add("hidden");
      editDiv.classList.remove("hidden");
    };
    cancelBtn.onclick = () => {
      clearInlineError(editDiv);
      displayDiv.classList.remove("hidden");
      editDiv.classList.add("hidden");
    };
    saveBtn.onclick = async () => {
      clearInlineError(editDiv);
      const res = await apiFetch("/api/dependencies", "PUT", {
        old_from: dep.from_member, old_to: dep.to_member,
        new_from: newFromSel.value, new_to: newToSel.value,
      });
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
  const from = document.getElementById("dep-from").value;
  const to   = document.getElementById("dep-to").value;
  const errEl = document.getElementById("dep-error");
  errEl.classList.add("hidden");
  if (!from || !to) return;
  const res = await apiFetch("/api/dependencies", "POST",
    { from_member: from, to_member: to });
  if (res.ok) {
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
  const names         = data.members.map(m => m.name).sort();

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
