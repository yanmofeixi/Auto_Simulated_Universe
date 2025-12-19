// 全局配置数据
let config = {};
let defaults = {};
let constants = {};
let isDirty = false; // 跟踪表单是否被修改
const API_BASE = "http://localhost:8520";

// 初始化
document.addEventListener("DOMContentLoaded", async () => {
  initTabs();
  await checkServer();
  await loadConstants();
  await loadDefaults();
  await loadConfig();
  initUI();
  initFormChangeListeners();
  setDirty(false); // 初始状态为未修改
});

// 检查服务器状态
async function checkServer() {
  try {
    const response = await fetch(`${API_BASE}/api/status`);
    if (response.ok) {
      document.getElementById("serverStatusText").textContent = "已连接";
      document.getElementById("serverStatusText").style.color =
        "var(--success)";
    } else {
      throw new Error("Server not responding");
    }
  } catch (e) {
    document.getElementById("serverStatusText").textContent = "未连接";
    document.getElementById("serverStatusText").style.color = "var(--danger)";
    showStatus("服务器未启动,请先运行 gui_server.py", "error");
  }
}

// 加载常量配置
async function loadConstants() {
  try {
    const response = await fetch(`${API_BASE}/api/constants`);
    if (response.ok) {
      constants = await response.json();
    }
  } catch (e) {
    console.error("Failed to load constants:", e);
  }
}

// 加载默认配置
async function loadDefaults() {
  try {
    const response = await fetch(`${API_BASE}/api/defaults`);
    if (response.ok) {
      defaults = await response.json();
    }
  } catch (e) {
    console.error("Failed to load defaults:", e);
  }
}

// 加载配置
async function loadConfig() {
  showStatus("加载配置中...", "loading");
  try {
    const response = await fetch(`${API_BASE}/api/config`);
    if (response.ok) {
      config = await response.json();
      populateForm();
      showStatus("配置加载成功", "success");
    } else {
      throw new Error("Failed to load config");
    }
  } catch (e) {
    console.error("Failed to load config:", e);
    showStatus("加载配置失败", "error");
  }
}

// 初始化 UI 组件
function initUI() {
  initDifficultySelector();
  initTimezoneSelector();
  initTeamSelector();
  initSkillSelector();
  initPortalPriority();
  initFateSelector();
  initSecondaryFateSelector();
  initOrderSelector();
  initFateBlessings();
}

// 初始化难度选择器
function initDifficultySelector() {
  const select = document.getElementById("difficulty");
  const currentDifficulty =
    config.config?.difficulty ?? constants.default_difficulty ?? 5;
  const difficultyLabels = ["简单", "普通", "困难", "噩梦", "最高"];

  select.innerHTML = [1, 2, 3, 4, 5]
    .map(
      (d) =>
        `<option value="${d}" ${
          d === currentDifficulty ? "selected" : ""
        }>${d} - ${difficultyLabels[d - 1]}</option>`
    )
    .join("");
}

// 初始化时区选择器
function initTimezoneSelector() {
  const select = document.getElementById("timezone");
  const currentTimezone =
    config.config?.timezone || constants.default_timezone || "Default";
  const timezones = constants.timezones || [];

  select.innerHTML = timezones
    .map(
      (tz) =>
        `<option value="${tz.value}" ${
          tz.value === currentTimezone ? "selected" : ""
        }>${tz.label}</option>`
    )
    .join("");
}

// 初始化队伍类型选择器
function initTeamSelector() {
  const select = document.getElementById("team");
  const currentTeam = config.config?.team || constants.default_team || "终结技";
  const teamTypes = constants.team_types || [];

  select.innerHTML = teamTypes
    .map(
      (t) =>
        `<option value="${t}" ${
          t === currentTeam ? "selected" : ""
        }>${t}</option>`
    )
    .join("");
}

// 初始化秘技角色选择器
function initSkillSelector() {
  const container = document.getElementById("skillSelector");
  const skills = config.config?.skill || constants.default_skills || [];
  const characters = constants.characters || [];

  container.innerHTML = "";
  for (let i = 0; i < 4; i++) {
    const div = document.createElement("div");
    div.className = "skill-item";
    div.innerHTML = `
      <span class="slot-label">角色 ${i + 1}</span>
      <select id="skill_${i}">
        <option value="">-- 不选择 --</option>
        ${characters
          .map(
            (c) =>
              `<option value="${c}" ${
                skills[i] === c ? "selected" : ""
              }>${c}</option>`
          )
          .join("")}
      </select>
    `;
    container.appendChild(div);
  }
}

// 初始化传送门优先级(拖拽排序)
function initPortalPriority() {
  const container = document.getElementById("portalPriorityList");
  const portalPrior =
    config.config?.portal_prior || constants.default_portal_prior || {};
  const portalTypes = constants.portal_types || [];

  // 按优先级排序(高优先级在前)
  const sortedTypes = [...portalTypes].sort(
    (a, b) => (portalPrior[b] || 1) - (portalPrior[a] || 1)
  );

  container.innerHTML = "";
  sortedTypes.forEach((type, index) => {
    const div = document.createElement("div");
    div.className = "sortable-item";
    div.draggable = true;
    div.dataset.type = type;
    div.innerHTML = `
      <span class="drag-handle">☰</span>
      <span class="item-rank">${portalTypes.length - index}</span>
      <span class="item-label">${type}</span>
    `;
    container.appendChild(div);
  });

  // 初始化拖拽排序
  initSortable(container);
}

// 拖拽排序功能
function initSortable(container) {
  let draggedItem = null;

  container.addEventListener("dragstart", (e) => {
    if (e.target.classList.contains("sortable-item")) {
      draggedItem = e.target;
      e.target.classList.add("dragging");
    }
  });

  container.addEventListener("dragend", (e) => {
    if (e.target.classList.contains("sortable-item")) {
      e.target.classList.remove("dragging");
      draggedItem = null;
      updateRanks(container);
    }
  });

  container.addEventListener("dragover", (e) => {
    e.preventDefault();
    const afterElement = getDragAfterElement(container, e.clientY);
    if (draggedItem) {
      if (afterElement == null) {
        container.appendChild(draggedItem);
      } else {
        container.insertBefore(draggedItem, afterElement);
      }
    }
  });
}

function getDragAfterElement(container, y) {
  const draggableElements = [
    ...container.querySelectorAll(".sortable-item:not(.dragging)"),
  ];

  return draggableElements.reduce(
    (closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset: offset, element: child };
      } else {
        return closest;
      }
    },
    { offset: Number.NEGATIVE_INFINITY }
  ).element;
}

function updateRanks(container) {
  const items = container.querySelectorAll(".sortable-item");
  const total = items.length;
  items.forEach((item, index) => {
    const rankEl = item.querySelector(".item-rank");
    if (rankEl) {
      rankEl.textContent = total - index;
    }
  });
}

// 初始化命途选择器
function initFateSelector() {
  const select = document.getElementById("fate");
  const currentFate = config.config?.fate || constants.default_fate || "巡猎";
  const fates = constants.fates || [];

  select.innerHTML = fates
    .map(
      (f) =>
        `<option value="${f}" ${
          f === currentFate ? "selected" : ""
        }>${f}</option>`
    )
    .join("");
}

// 初始化次要命途选择器
function initSecondaryFateSelector() {
  const container = document.getElementById("secondaryFateSelector");
  const secondaryFates =
    config.config?.secondary_fate || constants.default_secondary_fates || [];
  const fates = constants.fates || [];

  container.innerHTML = fates
    .map(
      (f) => `
    <div class="fate-chip ${secondaryFates.includes(f) ? "selected" : ""}"
         data-fate="${f}" onclick="toggleSecondaryFate(this)">
      ${f}
    </div>
  `
    )
    .join("");
}

// 切换次要命途
function toggleSecondaryFate(el) {
  el.classList.toggle("selected");
}

// 初始化优先级顺序选择器
function initOrderSelector() {
  const container = document.getElementById("orderSelector");
  const orderText = config.config?.order_text ||
    constants.default_order_text || [1, 2, 3, 4];

  container.innerHTML = orderText
    .map(
      (order, i) => `
    <div class="order-item">
      <span>位置 ${i + 1}:</span>
      <select id="order_${i}">
        ${[1, 2, 3, 4]
          .map(
            (v) =>
              `<option value="${v}" ${
                order === v ? "selected" : ""
              }>${v}</option>`
          )
          .join("")}
      </select>
    </div>
  `
    )
    .join("");
}

// 初始化命途祝福配置
function initFateBlessings() {
  const container = document.getElementById("fateBlessingsContainer");
  const prior = config.prior || defaults.simul_prior || {};
  const fates = constants.fates || [];

  container.innerHTML = fates
    .map(
      (fate) => `
    <div class="form-group" style="margin-bottom: 1rem;">
      <label>${fate} 祝福优先列表</label>
      <div class="list-editor">
        <textarea id="prior_${fate}" rows="4">${(prior[fate] || []).join(
        "\n"
      )}</textarea>
      </div>
    </div>
  `
    )
    .join("");
}

// 填充表单
function populateForm() {
  const cfg = config.config || {};
  const prior = config.prior || {};

  // 通用配置
  document.getElementById("angle").value =
    cfg.angle ?? constants.default_angle ?? 1.0;
  document.getElementById("difficulty").value =
    cfg.difficulty ?? constants.default_difficulty ?? 5;

  // 差分宇宙配置
  document.getElementById("accuracy").value =
    cfg.accuracy ?? constants.default_accuracy ?? 1440;
  document.getElementById("ocr_use_gpu").checked = cfg.ocr_use_gpu ?? false;

  // 模拟宇宙配置
  document.getElementById("use_consumable").checked = cfg.use_consumable === 1;

  // 优先级列表
  document.getElementById("prior_curio").value = (prior["奇物"] || []).join(
    "\n"
  );
  document.getElementById("prior_event").value = (prior["事件"] || []).join(
    "\n"
  );
}

// 收集表单数据
function collectFormData() {
  const portalTypes = constants.portal_types || [];
  const fates = constants.fates || [];

  const cfg = {
    // 通用配置
    angle: parseFloat(document.getElementById("angle").value),
    difficulty: parseInt(document.getElementById("difficulty").value),
    timezone: document.getElementById("timezone").value,

    // 差分宇宙配置
    accuracy: parseInt(document.getElementById("accuracy").value),
    ocr_use_gpu: document.getElementById("ocr_use_gpu").checked,
    team: document.getElementById("team").value,
    enable_portal_prior: 1,
    portal_prior: {},
    skill: [],

    // 模拟宇宙配置
    fate: document.getElementById("fate").value,
    use_consumable: document.getElementById("use_consumable").checked ? 1 : 0,
    secondary_fate: [],
    order_text: [],
    map_sha: config.config?.map_sha || "",
  };

  // 收集秘技角色
  for (let i = 0; i < 4; i++) {
    const val = document.getElementById(`skill_${i}`).value;
    if (val) cfg.skill.push(val);
  }

  // 收集传送门优先级(从拖拽排序列表)
  const portalItems = document.querySelectorAll(
    "#portalPriorityList .sortable-item"
  );
  const totalPortals = portalItems.length;
  portalItems.forEach((item, index) => {
    const type = item.dataset.type;
    cfg.portal_prior[type] = totalPortals - index;
  });

  // 收集次要命途
  document
    .querySelectorAll("#secondaryFateSelector .fate-chip.selected")
    .forEach((el) => {
      cfg.secondary_fate.push(el.dataset.fate);
    });

  // 收集优先级顺序
  for (let i = 0; i < 4; i++) {
    cfg.order_text.push(parseInt(document.getElementById(`order_${i}`).value));
  }

  // 收集优先级配置
  const prior = {
    奇物: document
      .getElementById("prior_curio")
      .value.split("\n")
      .filter((s) => s.trim()),
    事件: document
      .getElementById("prior_event")
      .value.split("\n")
      .filter((s) => s.trim()),
  };

  // 收集各命途祝福
  fates.forEach((fate) => {
    const textarea = document.getElementById(`prior_${fate}`);
    if (textarea) {
      prior[fate] = textarea.value.split("\n").filter((s) => s.trim());
    }
  });

  return { config: cfg, prior: prior };
}

// 保存配置
document.getElementById("configForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!isDirty) {
    showStatus("配置未修改", "info");
    return;
  }

  showStatus("保存中...", "loading");
  const data = collectFormData();

  try {
    const response = await fetch(`${API_BASE}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (response.ok) {
      setDirty(false);
      showStatus("配置保存成功!", "success");
    } else {
      throw new Error("Save failed");
    }
  } catch (e) {
    console.error("Failed to save config:", e);
    showStatus("保存失败", "error");
  }
});

// 重置配置
async function resetConfig() {
  if (!confirm("确定要重置为默认配置吗?")) return;

  try {
    const response = await fetch(`${API_BASE}/api/config/reset`, {
      method: "POST",
    });
    if (response.ok) {
      await loadConfig();
      initUI();
      showStatus("已重置为默认配置", "success");
    }
  } catch (e) {
    showStatus("重置失败", "error");
  }
}

// 启动程序
async function launchProgram(mode) {
  const btn = document.querySelector(`.launch-btn.${mode}`);
  btn.disabled = true;
  showStatus(
    `正在启动${mode === "diver" ? "差分宇宙" : "模拟宇宙"}...`,
    "loading"
  );

  try {
    const response = await fetch(`${API_BASE}/api/launch/${mode}`, {
      method: "POST",
    });
    if (response.ok) {
      showStatus(
        `${mode === "diver" ? "差分宇宙" : "模拟宇宙"}已启动!`,
        "success"
      );
    } else {
      throw new Error("Launch failed");
    }
  } catch (e) {
    showStatus("启动失败,请检查服务器状态", "error");
  } finally {
    btn.disabled = false;
  }
}

// 显示状态消息
function showStatus(msg, type = "") {
  const el = document.getElementById("statusMessage");
  el.className = `status-message ${type}`;

  if (type === "loading") {
    el.innerHTML = `<div class="spinner"></div><span>${msg}</span>`;
  } else {
    el.innerHTML = `<span>${msg}</span>`;
  }
}

// Tab 切换
function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab-btn")
        .forEach((b) => b.classList.remove("active"));
      document
        .querySelectorAll(".tab-content")
        .forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

// 脏状态管理
function setDirty(dirty) {
  isDirty = dirty;
  const saveBtn = document.querySelector('button[type="submit"]');
  if (saveBtn) {
    if (dirty) {
      saveBtn.classList.add("dirty");
      saveBtn.classList.remove("clean");
    } else {
      saveBtn.classList.remove("dirty");
      saveBtn.classList.add("clean");
    }
  }
}

// 监听表单变化
function initFormChangeListeners() {
  const form = document.getElementById("configForm");

  // 监听所有 input, select, textarea 变化
  form.addEventListener("input", () => setDirty(true));
  form.addEventListener("change", () => setDirty(true));

  // 监听拖拽排序完成
  const portalList = document.getElementById("portalPriorityList");
  if (portalList) {
    portalList.addEventListener("dragend", () => setDirty(true));
  }

  // 监听次要命途点击
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("fate-chip")) {
      setDirty(true);
    }
  });
}
