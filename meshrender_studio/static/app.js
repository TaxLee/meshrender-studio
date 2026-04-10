const state = {
  projectId: null,
  project: null,
  job: null,
  pollHandle: null,
};

const SOURCE_KINDS = ["auto", "abaqus_inp", "aqwa_lis", "vtu", "vtk"];
const ANGLE_LIMITS = {
  min: -180,
  max: 180,
  step: 1,
};
const DEFAULT_ZOOM_INSET = {
  enabled: false,
  view: "",
  crop_box: [0.05, 0.54, 0.22, 0.26],
  inset_box: [0.37, 0.08, 0.35, 0.35],
  stroke_color: [0.95, 0.43, 0.16],
  stroke_width: 4,
};

function $(id) {
  return document.getElementById(id);
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function showError(message) {
  $("job-error").textContent = message;
  $("job-error").classList.add("danger");
}

function clearError() {
  $("job-error").textContent = "None";
  $("job-error").classList.remove("danger");
}

function csvToArray(text) {
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function arrayToCsv(values) {
  return (values || []).join(", ");
}

function parseNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function parseVector(text) {
  const values = csvToArray(text).map(Number);
  if (values.length !== 3 || values.some((value) => Number.isNaN(value))) {
    throw new Error(`Expected three comma-separated numbers, got: ${text}`);
  }
  return values;
}

function parseNormalizedRect(text) {
  const values = csvToArray(text).map(Number);
  if (values.length !== 4 || values.some((value) => Number.isNaN(value))) {
    throw new Error(`Expected four comma-separated numbers, got: ${text}`);
  }
  const [x, y, width, height] = values;
  if (width <= 0 || height <= 0) {
    throw new Error(`Expected positive width and height, got: ${text}`);
  }
  if (x < 0 || y < 0 || x + width > 1 || y + height > 1) {
    throw new Error(`Expected values inside 0..1 bounds, got: ${text}`);
  }
  return values;
}

function applyInsetValue(handler) {
  return (value) => {
    try {
      handler(value);
      clearError();
    } catch (error) {
      showError(error.message);
    }
  };
}

function availableSourceViews(source) {
  const configuredViews = state.project.views.map((view) => view.name).filter(Boolean);
  const selectedViews = (source.views || []).filter((viewName) => configuredViews.includes(viewName));
  return selectedViews.length ? selectedViews : configuredViews;
}

function ensureZoomInset(source) {
  const availableViews = availableSourceViews(source);
  const fallbackView = availableViews[0] || "";
  if (!source.zoom_inset) {
    source.zoom_inset = clone(DEFAULT_ZOOM_INSET);
  }
  source.zoom_inset.enabled = Boolean(source.zoom_inset.enabled);
  source.zoom_inset.view = availableViews.includes(source.zoom_inset.view)
    ? source.zoom_inset.view
    : fallbackView;
  source.zoom_inset.crop_box = Array.isArray(source.zoom_inset.crop_box)
    ? source.zoom_inset.crop_box.map(Number)
    : clone(DEFAULT_ZOOM_INSET.crop_box);
  source.zoom_inset.inset_box = Array.isArray(source.zoom_inset.inset_box)
    ? source.zoom_inset.inset_box.map(Number)
    : clone(DEFAULT_ZOOM_INSET.inset_box);
  source.zoom_inset.stroke_color = Array.isArray(source.zoom_inset.stroke_color)
    ? source.zoom_inset.stroke_color.map(Number)
    : clone(DEFAULT_ZOOM_INSET.stroke_color);
  source.zoom_inset.stroke_width = Number(source.zoom_inset.stroke_width ?? DEFAULT_ZOOM_INSET.stroke_width);
  return source.zoom_inset;
}

function renderProjectInfo() {
  $("project-id").textContent = state.projectId || "Not loaded";
  $("project-name").value = state.project?.project_name || "";
}

function createInput(value, onChange, { type = "text", placeholder = "", step = "" } = {}) {
  const input = document.createElement("input");
  input.type = type;
  input.value = value ?? "";
  input.placeholder = placeholder;
  if (step !== "") {
    input.step = step;
  }
  input.addEventListener("change", (event) => onChange(event.target.value));
  return input;
}

function createNumberInput(value, onChange, { step = "" } = {}) {
  return createInput(value, (nextValue) => onChange(Number(nextValue || 0)), {
    type: "number",
    step,
  });
}

function createAngleControl(value, onChange) {
  const wrapper = document.createElement("div");
  wrapper.className = "angle-control";

  const slider = document.createElement("input");
  slider.type = "range";
  slider.min = String(ANGLE_LIMITS.min);
  slider.max = String(ANGLE_LIMITS.max);
  slider.step = String(ANGLE_LIMITS.step);
  slider.className = "angle-slider";

  const number = document.createElement("input");
  number.type = "number";
  number.min = String(ANGLE_LIMITS.min);
  number.max = String(ANGLE_LIMITS.max);
  number.step = String(ANGLE_LIMITS.step);
  number.className = "angle-number";

  const unit = document.createElement("span");
  unit.className = "angle-unit";
  unit.textContent = "°";

  let currentValue = clamp(parseNumber(value, 0), ANGLE_LIMITS.min, ANGLE_LIMITS.max);

  function sync(nextValue) {
    currentValue = clamp(parseNumber(nextValue, currentValue), ANGLE_LIMITS.min, ANGLE_LIMITS.max);
    slider.value = String(currentValue);
    number.value = String(currentValue);
    onChange(currentValue);
  }

  slider.addEventListener("input", (event) => sync(event.target.value));
  number.addEventListener("input", (event) => sync(event.target.value));
  number.addEventListener("change", (event) => sync(event.target.value));
  sync(currentValue);

  wrapper.appendChild(slider);
  wrapper.appendChild(number);
  wrapper.appendChild(unit);
  return wrapper;
}

function createCheckbox(checked, onChange) {
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = Boolean(checked);
  input.addEventListener("change", (event) => onChange(event.target.checked));
  return input;
}

function createSelect(options, value, onChange) {
  const select = document.createElement("select");
  options.forEach((optionValue) => {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue;
    if (optionValue === value) {
      option.selected = true;
    }
    select.appendChild(option);
  });
  select.addEventListener("change", (event) => onChange(event.target.value));
  return select;
}

function renderSources() {
  const body = $("sources-body");
  body.innerHTML = "";

  if (!state.project.sources.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 9;
    cell.className = "empty-state";
    cell.textContent = "No sources added yet. Import files or add a manual row.";
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }

  state.project.sources.forEach((source, index) => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.appendChild(
      createInput(source.name || "", (value) => {
        source.name = value;
      })
    );
    row.appendChild(nameCell);

    const kindCell = document.createElement("td");
    kindCell.appendChild(
      createSelect(SOURCE_KINDS, source.kind || "auto", (value) => {
        source.kind = value;
      })
    );
    row.appendChild(kindCell);

    const inputCell = document.createElement("td");
    inputCell.appendChild(
      createInput(source.input || "", (value) => {
        source.input = value;
      })
    );
    row.appendChild(inputCell);

    const prefixCell = document.createElement("td");
    prefixCell.appendChild(
      createInput(source.figure_prefix || "", (value) => {
        source.figure_prefix = value;
      })
    );
    row.appendChild(prefixCell);

    const viewsCell = document.createElement("td");
    viewsCell.appendChild(
      createInput(arrayToCsv(source.views || []), (value) => {
        source.views = csvToArray(value);
      }, { placeholder: "oblique, profile" })
    );
    row.appendChild(viewsCell);

    const partNameCell = document.createElement("td");
    partNameCell.appendChild(
      createInput(source.part_name || "", (value) => {
        source.part_name = value;
      })
    );
    row.appendChild(partNameCell);

    const partIndexCell = document.createElement("td");
    partIndexCell.appendChild(
      createNumberInput(source.part_index ?? 0, (value) => {
        source.part_index = value;
      })
    );
    row.appendChild(partIndexCell);

    const structureCell = document.createElement("td");
    structureCell.appendChild(
      createInput(source.structure_filter ?? "", (value) => {
        source.structure_filter = value;
      })
    );
    row.appendChild(structureCell);

    const actionCell = document.createElement("td");
    const removeButton = document.createElement("button");
    removeButton.className = "secondary";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => {
      state.project.sources.splice(index, 1);
      renderAll();
    });
    actionCell.appendChild(removeButton);
    row.appendChild(actionCell);

    body.appendChild(row);
  });
}

function renderViews() {
  const body = $("views-body");
  body.innerHTML = "";

  state.project.views.forEach((view, index) => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.appendChild(
      createInput(view.name || "", (value) => {
        view.name = value;
      })
    );
    row.appendChild(nameCell);

    const azimuthCell = document.createElement("td");
    azimuthCell.appendChild(
      createAngleControl(view.azimuth ?? 0, (value) => {
        view.azimuth = value;
      })
    );
    row.appendChild(azimuthCell);

    const elevationCell = document.createElement("td");
    elevationCell.appendChild(
      createAngleControl(view.elevation ?? 0, (value) => {
        view.elevation = value;
      })
    );
    row.appendChild(elevationCell);

    const rollCell = document.createElement("td");
    rollCell.appendChild(
      createAngleControl(view.roll ?? 0, (value) => {
        view.roll = value;
      })
    );
    row.appendChild(rollCell);

    const zoomCell = document.createElement("td");
    zoomCell.appendChild(
      createNumberInput(view.zoom_factor ?? 1, (value) => {
        view.zoom_factor = value;
      }, { step: "0.1" })
    );
    row.appendChild(zoomCell);

    const parallelCell = document.createElement("td");
    parallelCell.appendChild(
      createCheckbox(
        view.parallel_projection ?? state.project.render_defaults.parallel_projection,
        (checked) => {
          view.parallel_projection = checked;
        }
      )
    );
    row.appendChild(parallelCell);

    const actionCell = document.createElement("td");
    const removeButton = document.createElement("button");
    removeButton.className = "secondary";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => {
      state.project.views.splice(index, 1);
      renderAll();
    });
    actionCell.appendChild(removeButton);
    row.appendChild(actionCell);

    body.appendChild(row);
  });
}

function renderInsets() {
  const container = $("inset-configs");
  container.innerHTML = "";

  if (!state.project.sources.length) {
    container.innerHTML = '<p class="empty-state">Add a source before defining a zoom inset.</p>';
    return;
  }

  state.project.sources.forEach((source) => {
    const inset = ensureZoomInset(source);
    const availableViews = availableSourceViews(source);

    const card = document.createElement("article");
    card.className = "inset-card";

    const title = document.createElement("h3");
    title.textContent = source.name || source.figure_prefix || "Unnamed source";
    card.appendChild(title);

    const note = document.createElement("p");
    note.className = "inset-note";
    note.textContent = availableViews.length
      ? `Applied only to the ${availableViews.join(", ")} render view${availableViews.length > 1 ? "s" : ""}.`
      : "This source does not currently reference any valid view.";
    card.appendChild(note);

    const grid = document.createElement("div");
    grid.className = "inset-grid";

    const enabledField = document.createElement("label");
    const enabledTitle = document.createElement("span");
    enabledTitle.textContent = "Enable inset";
    enabledField.appendChild(enabledTitle);
    enabledField.appendChild(
      createCheckbox(inset.enabled, (checked) => {
        inset.enabled = checked;
      })
    );
    grid.appendChild(enabledField);

    const viewField = document.createElement("label");
    const viewTitle = document.createElement("span");
    viewTitle.textContent = "Target view";
    viewField.appendChild(viewTitle);
    viewField.appendChild(
      createSelect(availableViews.length ? availableViews : [""], inset.view, (value) => {
        inset.view = value;
      })
    );
    grid.appendChild(viewField);

    const cropField = document.createElement("label");
    const cropTitle = document.createElement("span");
    cropTitle.textContent = "Crop box";
    cropField.appendChild(cropTitle);
    cropField.appendChild(
      createInput(arrayToCsv(inset.crop_box), applyInsetValue((value) => {
        inset.crop_box = parseNormalizedRect(value);
      }), { placeholder: "0.05, 0.54, 0.22, 0.26" })
    );
    grid.appendChild(cropField);

    const insetField = document.createElement("label");
    const insetTitle = document.createElement("span");
    insetTitle.textContent = "Inset box";
    insetField.appendChild(insetTitle);
    insetField.appendChild(
      createInput(arrayToCsv(inset.inset_box), applyInsetValue((value) => {
        inset.inset_box = parseNormalizedRect(value);
      }), { placeholder: "0.37, 0.08, 0.35, 0.35" })
    );
    grid.appendChild(insetField);

    const colorField = document.createElement("label");
    const colorTitle = document.createElement("span");
    colorTitle.textContent = "Outline color";
    colorField.appendChild(colorTitle);
    colorField.appendChild(
      createInput(arrayToCsv(inset.stroke_color), applyInsetValue((value) => {
        inset.stroke_color = parseVector(value);
      }), { placeholder: "0.95, 0.43, 0.16" })
    );
    grid.appendChild(colorField);

    const widthField = document.createElement("label");
    const widthTitle = document.createElement("span");
    widthTitle.textContent = "Outline width";
    widthField.appendChild(widthTitle);
    widthField.appendChild(
      createNumberInput(inset.stroke_width, applyInsetValue((value) => {
        const width = Number(value || 0);
        if (width <= 0) {
          throw new Error("Outline width must be positive.");
        }
        inset.stroke_width = width;
      }), { step: "0.5" })
    );
    grid.appendChild(widthField);

    card.appendChild(grid);
    container.appendChild(card);
  });
}

function renderRenderDefaults() {
  const container = $("render-defaults");
  container.innerHTML = "";
  const defaults = state.project.render_defaults;

  const fields = [
    ["Image width", defaults.image_width, (value) => { defaults.image_width = Number(value || 0); }],
    ["Image height", defaults.image_height, (value) => { defaults.image_height = Number(value || 0); }],
    ["Background", arrayToCsv(defaults.background), (value) => { defaults.background = parseVector(value); }],
    ["Surface color", arrayToCsv(defaults.surface_color), (value) => { defaults.surface_color = parseVector(value); }],
    ["Edge color", arrayToCsv(defaults.edge_color), (value) => { defaults.edge_color = parseVector(value); }],
    ["Line width", defaults.line_width, (value) => { defaults.line_width = Number(value || 0); }],
    ["Surface opacity", defaults.surface_opacity, (value) => { defaults.surface_opacity = Number(value || 0); }],
  ];

  fields.forEach(([label, value, handler]) => {
    const wrapper = document.createElement("label");
    const title = document.createElement("span");
    title.textContent = label;
    wrapper.appendChild(title);
    const input = createInput(value, (nextValue) => {
      try {
        handler(nextValue);
        clearError();
      } catch (error) {
        showError(error.message);
      }
    });
    wrapper.appendChild(input);
    container.appendChild(wrapper);
  });

  const parallelWrapper = document.createElement("label");
  const parallelTitle = document.createElement("span");
  parallelTitle.textContent = "Parallel projection";
  parallelWrapper.appendChild(parallelTitle);
  parallelWrapper.appendChild(
    createCheckbox(defaults.parallel_projection, (checked) => {
      defaults.parallel_projection = checked;
    })
  );
  container.appendChild(parallelWrapper);
}

function renderSavedProjects(projects) {
  const select = $("saved-projects");
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = projects.length ? "Select saved project" : "No saved projects";
  select.appendChild(placeholder);
  projects.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.project_id;
    option.textContent = `${project.project_name} (${project.project_id})`;
    select.appendChild(option);
  });
}

function renderResults() {
  const gallery = $("results-gallery");
  const meshLinks = $("mesh-links");
  gallery.innerHTML = "";
  meshLinks.innerHTML = "";

  if (!state.job || !state.job.outputs) {
    gallery.innerHTML = '<p class="empty-state">No job results yet.</p>';
    return;
  }

  const figures = state.job.outputs.figures || [];
  const mesh = state.job.outputs.mesh || [];

  if (!figures.length) {
    gallery.innerHTML = '<p class="empty-state">No figure outputs available.</p>';
  } else {
    figures.forEach((item) => {
      const card = document.createElement("article");
      card.className = "gallery-card";
      const title = document.createElement("h3");
      title.textContent = item.name;
      const image = document.createElement("img");
      image.src = `${item.url}?ts=${Date.now()}`;
      image.alt = item.name;
      card.appendChild(title);
      card.appendChild(image);
      gallery.appendChild(card);
    });
  }

  mesh.forEach((item) => {
    const link = document.createElement("a");
    link.href = item.url;
    link.textContent = item.name;
    link.target = "_blank";
    meshLinks.appendChild(link);
  });
}

function renderJob() {
  $("job-state").textContent = state.job?.status || "Idle";
  $("job-log").textContent = state.job?.logs?.join("\n") || "";
  if (state.job?.error) {
    showError(state.job.error);
  } else {
    clearError();
  }
  renderResults();
}

function renderAll() {
  renderProjectInfo();
  renderSources();
  renderViews();
  renderInsets();
  renderRenderDefaults();
  renderJob();
}

async function refreshProjects() {
  const data = await requestJson("/api/projects");
  renderSavedProjects(data.projects);
}

async function loadTemplate() {
  const data = await requestJson("/api/project/template");
  state.projectId = data.project_id;
  state.project = data.project;
  state.job = null;
  renderAll();
}

async function loadSystemStatus() {
  const data = await requestJson("/api/system");
  $("pvpython-status").textContent = data.available ? data.pvpython : `Unavailable: ${data.error}`;
}

async function handleImport(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length || !state.projectId) {
    return;
  }
  const formData = new FormData();
  formData.append("project_id", state.projectId);
  files.forEach((file) => formData.append("files", file));

  try {
    const data = await requestJson("/api/project/import-files", {
      method: "POST",
      body: formData,
    });
    data.files.forEach((item) => state.project.sources.push(item.source));
    renderAll();
    event.target.value = "";
  } catch (error) {
    showError(error.message);
  }
}

async function saveProject() {
  try {
    const data = await requestJson("/api/project/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: state.projectId,
        project: state.project,
      }),
    });
    state.project = data.project;
    renderAll();
    await refreshProjects();
  } catch (error) {
    showError(error.message);
  }
}

async function loadSelectedProject() {
  const projectId = $("saved-projects").value;
  if (!projectId) {
    return;
  }
  try {
    const data = await requestJson("/api/project/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId }),
    });
    state.projectId = data.project_id;
    state.project = data.project;
    state.job = null;
    renderAll();
  } catch (error) {
    showError(error.message);
  }
}

function addManualSource() {
  state.project.sources.push({
    name: "new_source",
    kind: "auto",
    input: "",
    figure_prefix: "new_source",
    views: state.project.views.length ? [state.project.views[0].name] : [],
    zoom_inset: clone({
      ...DEFAULT_ZOOM_INSET,
      view: state.project.views[0]?.name || "",
    }),
    part_name: "",
    part_index: 0,
    structure_filter: "",
  });
  renderAll();
}

function addView() {
  state.project.views.push({
    name: `view_${state.project.views.length + 1}`,
    azimuth: 58,
    elevation: 28,
    roll: -8,
    zoom_factor: 1,
    parallel_projection: true,
  });
  renderAll();
}

async function pollJob(jobId) {
  if (!jobId) {
    return;
  }
  try {
    const data = await requestJson(`/api/jobs/${jobId}`);
    state.job = data;
    renderJob();
    if (["completed", "failed"].includes(data.status)) {
      stopPolling();
    }
  } catch (error) {
    stopPolling();
    showError(error.message);
  }
}

function stopPolling() {
  if (state.pollHandle) {
    clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

function startPolling(jobId) {
  stopPolling();
  state.pollHandle = setInterval(() => pollJob(jobId), 1000);
}

async function runJob() {
  try {
    const data = await requestJson("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: state.projectId,
        project: state.project,
      }),
    });
    state.job = data;
    renderJob();
    startPolling(data.job_id);
  } catch (error) {
    showError(error.message);
  }
}

function bindEvents() {
  $("project-name").addEventListener("change", (event) => {
    state.project.project_name = event.target.value;
  });
  $("new-project-btn").addEventListener("click", loadTemplate);
  $("save-project-btn").addEventListener("click", saveProject);
  $("load-project-btn").addEventListener("click", loadSelectedProject);
  $("file-import").addEventListener("change", handleImport);
  $("add-source-btn").addEventListener("click", addManualSource);
  $("add-view-btn").addEventListener("click", addView);
  $("run-job-btn").addEventListener("click", runJob);
  $("refresh-job-btn").addEventListener("click", () => {
    if (state.job?.job_id) {
      pollJob(state.job.job_id);
    }
  });
}

async function init() {
  bindEvents();
  await loadTemplate();
  await refreshProjects();
  await loadSystemStatus();
}

init().catch((error) => {
  showError(error.message);
});
