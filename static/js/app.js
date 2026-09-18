(() => {
    "use strict";

    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => Array.from(document.querySelectorAll(selector));
    const PAGE_SIZE = 50;
    const ACTIVE_STATUSES = new Set(["pending", "running", "cancelling"]);
    const STORAGE_TASK_KEY = "knowledge-governance-current-task";

    const sourceMeta = {
        showdoc_public: {
            backend: "showdoc", name: "ShowDoc 公开项目", title: "公开项目配置", tag: "无需登录",
            notice: "填写公开项目编号后，可处理全部文档，也可以先加载目录并选择范围。",
            fieldsHint: "默认页编号只用于快速预览，不会限制最终采集范围。",
        },
        showdoc_account: {
            backend: "showdoc", name: "ShowDoc 账号项目", title: "账号项目配置", tag: "会话复用",
            notice: "首次登录后会复用当前服务中的登录会话，预览和任务执行无需重复登录。",
            fieldsHint: "登录并选择账号下的项目。服务重启或会话失效时才需要重新登录。",
        },
        cyb: {
            backend: "cyb", name: "云创业版知识库", title: "云创业版配置", tag: "自动登录",
            notice: "首次访问时自动登录并缓存会话，后续目录、预览和采集任务会复用登录状态。",
            fieldsHint: "无需填写连接参数。目录较大时，建议先选择少量文档验证结果。",
        },
        tiantong: {
            backend: "tiantong", name: "天通资源中心", title: "天通资源中心配置", tag: "公开资源",
            notice: "公开目录文档较多，可先使用关键词筛选，再选择部分文档执行。",
            fieldsHint: "无需登录。未填写关键词时，将读取完整公开目录。",
        },
        web: {
            backend: "web", name: "通用网页采集", title: "网页采集配置", tag: "公开网页",
            notice: "系统会提取网页正文，再执行结构规范、质量检查和知识分块。",
            fieldsHint: "仅支持 http 或 https 公网地址；同站模式不会跨主机发现页面。",
        },
    };

    const viewMeta = {
        collect: ["数据治理 / 数据采集", "采集工作台", "配置数据源与采集范围，生成可用于知识库的数据集。"],
        monitor: ["数据治理 / 任务监控", "任务监控", "查看采集、清洗、质量检查和数据集生成进度。"],
        datasets: ["数据治理 / 数据集", "数据集输出", "查看质量结果并下载已经生成的数据集。"],
    };

    const phaseOrder = ["connecting", "crawling", "cleaning", "quality_check", "packaging"];
    const phaseLabels = {
        queued: "等待执行", connecting: "连接与发现", crawling: "抓取正文", cleaning: "内容清洗",
        quality_check: "质量检查", packaging: "生成数据集", completed: "已完成", failed: "失败",
        cancelled: "已取消",
    };
    const statusLabels = {
        pending: "等待执行", running: "处理中", cancelling: "正在取消", completed: "已完成",
        failed: "失败", cancelled: "已取消",
    };

    const state = {
        source: "showdoc_public",
        view: "collect",
        step: "configure",
        pages: [],
        selectedIds: new Set(),
        pageNumber: 1,
        sourceStates: {},
        loggedIn: false,
        taskId: window.localStorage.getItem(STORAGE_TASK_KEY),
        task: null,
        tasks: [],
        pollTimer: null,
        modalTrigger: null,
        finishedNotices: new Set(),
    };

    async function request(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            const error = new Error(data.message || data.error || "请求失败");
            error.status = response.status;
            error.data = data;
            throw error;
        }
        return data;
    }

    function setVisible(element, visible) {
        element?.classList.toggle("hidden", !visible);
    }

    function notify(message, type = "info", options = {}) {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.setAttribute("role", type === "error" ? "alert" : "status");
        const copy = document.createElement("span");
        copy.textContent = message;
        const actions = document.createElement("div");
        actions.className = "toast-actions";
        if (typeof options.retry === "function") {
            const retry = document.createElement("button");
            retry.type = "button";
            retry.textContent = "重试";
            retry.addEventListener("click", () => { toast.remove(); options.retry(); });
            actions.appendChild(retry);
        }
        const close = document.createElement("button");
        close.type = "button";
        close.className = "toast-close";
        close.setAttribute("aria-label", "关闭提示");
        close.textContent = "×";
        close.addEventListener("click", () => toast.remove());
        actions.appendChild(close);
        toast.append(copy, actions);
        $("#toastStack").appendChild(toast);
        if (!(options.persistent ?? type === "error")) {
            window.setTimeout(() => toast.remove(), options.duration || 4200);
        }
    }

    function updateClock() {
        $("#currentTime").textContent = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    }

    function showView(view) {
        if (!viewMeta[view]) return;
        state.view = view;
        $$("[data-view-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.viewPanel === view));
        $$(".nav-item[data-view], .mobile-nav [data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
        const [eyebrow, title, subtitle] = viewMeta[view];
        $("#pageEyebrow").textContent = eyebrow;
        $("#pageTitle").textContent = title;
        $("#pageSubtitle").textContent = subtitle;
        if (view === "monitor") renderMonitorVisibility();
        if (view === "datasets") renderDatasets();
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function showStage(step) {
        if (step === "select" && !state.pages.length) {
            notify("请先加载文档目录", "warning");
            step = "configure";
        }
        state.step = step;
        $$("[data-stage]").forEach((stage) => setVisible(stage, stage.dataset.stage === step));
        $$(".flow-step[data-step]").forEach((item) => item.classList.toggle("active", item.dataset.step === step));
    }

    function captureSourceState() {
        state.sourceStates[state.source] = {
            itemId: $("#itemId").value,
            defaultPageId: $("#defaultPageId").value,
            projectId: $("#projectSelect").value,
            webUrl: $("#webUrl").value,
            webCrawlMode: $("#webCrawlMode").value,
            webMaxPages: $("#webMaxPages").value,
            webMaxDepth: $("#webMaxDepth").value,
            keyword: $("#keyword").value,
            downloadMode: $("#downloadMode").value,
            pages: state.pages,
            selectedIds: Array.from(state.selectedIds),
            pageNumber: state.pageNumber,
        };
    }

    function restoreSourceState(source) {
        const saved = state.sourceStates[source];
        if (!saved) {
            state.pages = [];
            state.selectedIds = new Set();
            state.pageNumber = 1;
            $("#keyword").value = "";
            $("#downloadMode").value = "all";
            $("#pageSearch").value = "";
            return;
        }
        $("#itemId").value = saved.itemId ?? $("#itemId").value;
        $("#defaultPageId").value = saved.defaultPageId ?? $("#defaultPageId").value;
        $("#webUrl").value = saved.webUrl || "";
        $("#webCrawlMode").value = saved.webCrawlMode || "page";
        $("#webMaxPages").value = saved.webMaxPages ?? "0";
        $("#webMaxDepth").value = saved.webMaxDepth ?? "0";
        $("#keyword").value = saved.keyword || "";
        $("#downloadMode").value = saved.downloadMode || "all";
        state.pages = saved.pages || [];
        state.selectedIds = new Set(saved.selectedIds || []);
        state.pageNumber = saved.pageNumber || 1;
        if (saved.projectId && Array.from($("#projectSelect").options).some((option) => option.value === saved.projectId)) {
            $("#projectSelect").value = saved.projectId;
        }
    }

    function clearValidation() {
        ["itemId", "projectSelect", "webUrl"].forEach((id) => $("#" + id)?.removeAttribute("aria-invalid"));
        ["itemIdError", "projectError", "webUrlError", "selectionError", "selectedStageError"].forEach((id) => { $("#" + id).textContent = ""; });
    }

    function setFieldError(inputId, errorId, message) {
        const input = $("#" + inputId);
        input?.setAttribute("aria-invalid", "true");
        $("#" + errorId).textContent = message;
        return input;
    }

    function setSource(source, options = {}) {
        if (!sourceMeta[source] || source === state.source && !options.initial) return;
        if (!options.initial) captureSourceState();
        state.source = source;
        restoreSourceState(source);
        clearValidation();
        const meta = sourceMeta[source];
        $$(".source-card").forEach((card) => card.classList.toggle("active", card.dataset.source === source));
        $("#configTitle").textContent = meta.title;
        $("#sourceTag").textContent = meta.tag;
        $("#sourceNotice").textContent = meta.notice;
        $("#sourceFieldsHint").textContent = meta.fieldsHint;
        $("#recordsSourceLabel").textContent = meta.name;
        setVisible($("#showdocPublicFields"), source === "showdoc_public");
        setVisible($("#showdocAccountFields"), source === "showdoc_account");
        setVisible($("#webFields"), source === "web");
        setVisible($("#genericFields"), source === "cyb" || source === "tiantong");
        setVisible($("#keywordField"), source !== "web");
        setVisible($("#downloadModeField"), source !== "web");
        $("#downloadMode").disabled = source === "web";
        if (source === "web") $("#downloadMode").value = "all";
        updateLoadButton();
        renderRecords();
        showStage(state.pages.length && $("#downloadMode").value === "selected" && options.keepStep ? "select" : "configure");
        if (source === "showdoc_account" && !state.loggedIn) loadShowdocProjects({ silent: true });
    }

    function updateLoadButton() {
        const chooseDocuments = state.source !== "web" && $("#downloadMode").value === "selected";
        setVisible($("#loadPagesButton"), chooseDocuments);
        setVisible($("#startButton"), !chooseDocuments);
    }

    function currentItemId() {
        return state.source === "showdoc_account" ? $("#projectSelect").value.trim() : $("#itemId").value.trim();
    }

    function validateConfig({ selection = false } = {}) {
        clearValidation();
        let firstInvalid = null;
        if (state.source === "showdoc_public" && !/^\d+$/.test($("#itemId").value.trim())) {
            firstInvalid = setFieldError("itemId", "itemIdError", "请输入有效的项目编号");
        }
        if (state.source === "showdoc_account" && !currentItemId()) {
            firstInvalid = setFieldError("projectSelect", "projectError", "请先登录并选择项目");
        }
        if (state.source === "web") {
            const value = $("#webUrl").value.trim();
            try {
                const url = new URL(value);
                if (!["http:", "https:"].includes(url.protocol)) throw new Error();
            } catch (_) {
                firstInvalid = setFieldError("webUrl", "webUrlError", "请输入有效的 http 或 https 地址");
            }
        }
        if (selection && state.selectedIds.size === 0) {
            $("#selectedStageError").textContent = "请至少选择一个文档";
            firstInvalid ||= $("#pageSearch");
        }
        firstInvalid?.focus();
        return !firstInvalid;
    }

    function buildDocumentsUrl() {
        const key = sourceMeta[state.source].backend;
        const params = new URLSearchParams();
        if (state.source === "showdoc_public" || state.source === "showdoc_account") {
            params.set("item_id", currentItemId());
            if ($("#keyword").value.trim()) params.set("keyword", $("#keyword").value.trim());
            if (state.source === "showdoc_public" && $("#defaultPageId").value.trim()) params.set("default_page_id", $("#defaultPageId").value.trim());
            if (state.source === "showdoc_account") params.set("auth", "1");
        } else if (state.source !== "web" && $("#keyword").value.trim()) {
            params.set("keyword", $("#keyword").value.trim());
        }
        return `/entries/${key}/documents${params.toString() ? `?${params}` : ""}`;
    }

    async function loadPages() {
        if (!validateConfig()) return;
        const button = $("#loadPagesButton");
        button.disabled = true;
        button.textContent = "正在加载目录…";
        try {
            const data = await request(buildDocumentsUrl());
            state.pages = data.pages || [];
            state.selectedIds = new Set(state.pages.map((page) => String(page.page_id)));
            state.pageNumber = 1;
            $("#pageSearch").value = "";
            captureSourceState();
            renderRecords();
            showStage("select");
            notify(`已加载 ${state.pages.length} 个文档`, "success");
        } catch (error) {
            notify(`目录加载失败：${error.message}`, "error", { retry: loadPages });
        } finally {
            button.disabled = false;
            button.innerHTML = "加载文档目录 <span>→</span>";
        }
    }

    function filteredPages() {
        const term = $("#pageSearch").value.trim().toLowerCase();
        if (!term) return state.pages;
        return state.pages.filter((page) => `${page.page_title || ""} ${page.category || ""}`.toLowerCase().includes(term));
    }

    function visiblePages() {
        const pages = filteredPages();
        const pageCount = Math.max(1, Math.ceil(pages.length / PAGE_SIZE));
        state.pageNumber = Math.min(Math.max(1, state.pageNumber), pageCount);
        return pages.slice((state.pageNumber - 1) * PAGE_SIZE, state.pageNumber * PAGE_SIZE);
    }

    function renderRecords() {
        const body = $("#recordsBody");
        const pages = visiblePages();
        $("#totalCount").textContent = state.pages.length;
        if (!pages.length) {
            body.innerHTML = '<tr><td colspan="5" class="empty-cell">没有匹配的文档</td></tr>';
        } else {
            body.innerHTML = pages.map((page) => {
                const id = String(page.page_id);
                return `<tr><td class="check-col"><input type="checkbox" data-page-id="${escapeAttr(id)}" ${state.selectedIds.has(id) ? "checked" : ""} aria-label="选择 ${escapeAttr(page.page_title || "未命名文档")}"></td><td><div class="doc-cell"><span class="doc-title">${escapeHtml(page.page_title || "未命名文档")}</span><span class="doc-id">编号 ${escapeHtml(id)}</span></div></td><td><span class="category-pill">${escapeHtml(page.category || "未分类")}</span></td><td><span class="state-pill">待治理</span></td><td><button type="button" class="link-button preview-page" data-page-id="${escapeAttr(id)}">预览</button></td></tr>`;
            }).join("");
        }
        updateSelectionMeta();
        updatePager();
    }

    function updateSelectionMeta() {
        $("#selectedCount").textContent = state.selectedIds.size;
        const pages = visiblePages();
        const selectedVisible = pages.filter((page) => state.selectedIds.has(String(page.page_id))).length;
        $("#selectVisible").checked = pages.length > 0 && selectedVisible === pages.length;
        $("#selectVisible").indeterminate = selectedVisible > 0 && selectedVisible < pages.length;
        $("#selectedStageError").textContent = "";
    }

    function updatePager() {
        const matches = filteredPages();
        const pageCount = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
        $("#pageLabel").textContent = `${state.pageNumber} / ${pageCount}`;
        $("#prevPage").disabled = state.pageNumber <= 1;
        $("#nextPage").disabled = state.pageNumber >= pageCount;
        $("#recordsHint").textContent = `每页最多显示 ${PAGE_SIZE} 条，当前搜索结果 ${matches.length} 条，勾选结果会跨页保留。`;
    }

    function selectFiltered(checked) {
        filteredPages().forEach((page) => {
            const id = String(page.page_id);
            if (checked) state.selectedIds.add(id); else state.selectedIds.delete(id);
        });
        captureSourceState();
        renderRecords();
    }

    function previewUrl(pageId) {
        const key = sourceMeta[state.source].backend;
        const params = new URLSearchParams({ doc_id: String(pageId) });
        if (key === "showdoc") {
            params.set("item_id", currentItemId());
            if (state.source === "showdoc_account") params.set("auth", "1");
        }
        return `/entries/${key}/preview?${params}`;
    }

    async function showPreview(pageId, title, trigger = document.activeElement) {
        state.modalTrigger = trigger;
        $("#previewTitle").textContent = title || "文档内容";
        $("#previewBody").innerHTML = '<div class="loading-state">正在加载内容…</div>';
        $("#previewModal").classList.remove("hidden");
        document.body.classList.add("modal-open");
        $("#closePreview").focus();
        try {
            const data = await request(previewUrl(pageId));
            $("#previewBody").innerHTML = markdownToHtml(data.content || "暂无内容");
        } catch (error) {
            $("#previewBody").innerHTML = `<div class="loading-state">加载失败：${escapeHtml(error.message)}</div>`;
        }
    }

    function closePreview() {
        if ($("#previewModal").classList.contains("hidden")) return;
        $("#previewModal").classList.add("hidden");
        document.body.classList.remove("modal-open");
        state.modalTrigger?.focus?.();
        state.modalTrigger = null;
    }

    function trapModalFocus(event) {
        if (event.key === "Escape") return closePreview();
        if (event.key !== "Tab" || $("#previewModal").classList.contains("hidden")) return;
        const focusable = $$("#previewModal button, #previewModal a[href], #previewModal [tabindex]:not([tabindex='-1'])").filter((item) => !item.disabled);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }

    function safeUrl(url) {
        const value = String(url || "").trim();
        return /^(https?:\/\/|assets\/|#)/i.test(value) ? value : "#";
    }

    function markdownToHtml(markdown) {
        const lines = escapeHtml(markdown).replace(/\r\n/g, "\n").split("\n");
        let html = "", inCode = false, code = [];
        lines.forEach((line) => {
            if (line.trim().startsWith("```") || line.trim().startsWith("~~~")) {
                if (inCode) { html += `<pre><code>${code.join("\n")}</code></pre>`; code = []; }
                inCode = !inCode;
                return;
            }
            if (inCode) { code.push(line); return; }
            const heading = line.match(/^(#{1,6})\s+(.+)$/);
            if (heading) { html += `<h${heading[1].length}>${inlineMarkdown(heading[2])}</h${heading[1].length}>`; return; }
            if (!line.trim()) return;
            if (/^[-*]\s+/.test(line)) { html += `<p>• ${inlineMarkdown(line.replace(/^[-*]\s+/, ""))}</p>`; return; }
            html += `<p>${inlineMarkdown(line)}</p>`;
        });
        if (inCode) html += `<pre><code>${code.join("\n")}</code></pre>`;
        return html || "<p>暂无内容</p>";
    }

    function inlineMarkdown(text) {
        let result = text.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_, alt, url) => `<img src="${escapeAttr(safeUrl(url))}" alt="${escapeAttr(alt || "图片")}">`);
        result = result.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) => `<a href="${escapeAttr(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${label}</a>`);
        return result.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>");
    }

    function buildStartPayload(useSelection) {
        const selectedIds = useSelection ? Array.from(state.selectedIds) : [];
        const payload = {
            selected_ids: selectedIds,
            selected_titles: useSelection ? state.pages.filter((page) => state.selectedIds.has(String(page.page_id))).map((page) => page.page_title) : [],
        };
        if (["showdoc_public", "showdoc_account"].includes(state.source)) {
            payload.item_id = currentItemId();
            payload.keyword = $("#keyword").value.trim();
            payload.auth = state.source === "showdoc_account";
            if (state.source === "showdoc_public") payload.default_page_id = $("#defaultPageId").value.trim();
        } else if (state.source === "web") {
            payload.url = $("#webUrl").value.trim();
            payload.crawl_mode = $("#webCrawlMode").value;
            payload.max_pages = Number($("#webMaxPages").value || 0);
            payload.max_depth = Number($("#webMaxDepth").value || 0);
        } else if ($("#keyword").value.trim()) {
            payload.keyword = $("#keyword").value.trim();
        }
        return payload;
    }

    function activeTask() {
        return state.tasks.find((task) => ACTIVE_STATUSES.has(task.status)) || (state.task && ACTIVE_STATUSES.has(state.task.status) ? state.task : null);
    }

    async function startJob({ useSelection = false } = {}) {
        if (!validateConfig({ selection: useSelection })) return;
        const existing = activeTask();
        if (existing) {
            state.taskId = existing.task_id;
            window.localStorage.setItem(STORAGE_TASK_KEY, state.taskId);
            await fetchTask(existing.task_id);
            showView("monitor");
            notify("已有任务正在处理，请等待完成或先取消当前任务。", "warning", { persistent: true });
            return;
        }
        const buttons = [$("#startButton"), $("#startSelectedButton")];
        buttons.forEach((button) => { button.disabled = true; });
        try {
            captureSourceState();
            const data = await request(`/entries/${sourceMeta[state.source].backend}/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(buildStartPayload(useSelection)),
            });
            state.taskId = data.task_id;
            window.localStorage.setItem(STORAGE_TASK_KEY, state.taskId);
            state.task = {
                task_id: data.task_id, entry: sourceMeta[state.source].backend, entry_name: sourceMeta[state.source].name,
                status: "pending", phase: "queued", progress: 0, message: "任务已提交，正在等待执行…", metrics: {}, logs: [],
                completed_pages: 0, total_pages: 0, successful_pages: 0, failed_pages: 0, skipped_pages: 0,
                start_time: new Date().toISOString(), elapsed_seconds: 0,
            };
            updateTaskUI(state.task);
            showView("monitor");
            await loadTasks({ preserveCurrent: true });
            startPolling();
            notify(data.message || "任务已开始", "success");
        } catch (error) {
            notify(`任务启动失败：${error.message}`, "error", { retry: () => startJob({ useSelection }) });
        } finally {
            updateActionAvailability();
        }
    }

    function stopPolling() {
        if (state.pollTimer) window.clearTimeout(state.pollTimer);
        state.pollTimer = null;
    }

    function startPolling() {
        stopPolling();
        const poll = async () => {
            if (!state.taskId) return;
            const task = await fetchTask(state.taskId, { notifyError: true });
            if (task && ACTIVE_STATUSES.has(task.status)) state.pollTimer = window.setTimeout(poll, 1600);
        };
        poll();
    }

    async function fetchTask(taskId, { notifyError = false } = {}) {
        try {
            const task = await request(`/task_status/${taskId}`);
            state.taskId = task.task_id;
            state.task = task;
            window.localStorage.setItem(STORAGE_TASK_KEY, task.task_id);
            updateTaskUI(task);
            mergeTask(task);
            if (!ACTIVE_STATUSES.has(task.status)) {
                stopPolling();
                loadTasks({ preserveCurrent: true });
                if (task.status === "completed" && !state.finishedNotices.has(task.task_id)) {
                    state.finishedNotices.add(task.task_id);
                    notify("治理任务完成，数据集已生成", "success");
                }
                if (task.status === "failed" && !state.finishedNotices.has(task.task_id)) {
                    state.finishedNotices.add(task.task_id);
                    notify(task.message || "任务执行失败", "error", { retry: retryCurrentTask });
                }
            }
            return task;
        } catch (error) {
            if (error.status === 404) {
                window.localStorage.removeItem(STORAGE_TASK_KEY);
                state.taskId = null;
                state.task = null;
                renderMonitorVisibility();
            }
            if (notifyError) notify(`任务状态获取失败：${error.message}`, "error", { retry: startPolling });
            return null;
        }
    }

    function mergeTask(task) {
        const index = state.tasks.findIndex((item) => item.task_id === task.task_id);
        const summary = { ...task, logs: undefined };
        if (index >= 0) state.tasks[index] = { ...state.tasks[index], ...summary };
        else state.tasks.unshift(summary);
        renderTaskLists();
    }

    async function loadTasks({ preserveCurrent = false } = {}) {
        try {
            const data = await request("/api/tasks");
            state.tasks = data.tasks || [];
            renderTaskLists();
            const stored = state.taskId || window.localStorage.getItem(STORAGE_TASK_KEY);
            const preferred = state.tasks.find((task) => task.task_id === stored)
                || state.tasks.find((task) => ACTIVE_STATUSES.has(task.status))
                || (!preserveCurrent ? state.tasks[0] : null);
            if (preferred && (!state.task || state.task.task_id !== preferred.task_id)) {
                await fetchTask(preferred.task_id);
                if (ACTIVE_STATUSES.has(preferred.status)) startPolling();
            } else if (!preferred && !state.task) {
                window.localStorage.removeItem(STORAGE_TASK_KEY);
                renderMonitorVisibility();
            }
        } catch (error) {
            notify(`任务列表加载失败：${error.message}`, "error", { retry: loadTasks });
        }
    }

    function renderTaskLists() {
        const activeCount = state.tasks.filter((task) => ACTIVE_STATUSES.has(task.status)).length;
        $("#navTaskBadge").textContent = activeCount;
        setVisible($("#navTaskBadge"), activeCount > 0);
        const sidebarTasks = state.tasks.slice(0, 6);
        $("#sidebarTasks").innerHTML = sidebarTasks.length ? sidebarTasks.map((task) => `<button class="sidebar-task ${task.task_id === state.taskId ? "active" : ""}" type="button" data-task-id="${escapeAttr(task.task_id)}"><span class="task-dot ${escapeAttr(task.status)}"></span><span><strong>${escapeHtml(task.entry_name || task.entry)}</strong><small>${escapeHtml(statusLabels[task.status] || task.status)} · ${formatDate(task.start_time)}</small></span></button>`).join("") : '<p class="sidebar-empty">暂无任务</p>';

        $("#taskHistory").innerHTML = state.tasks.length ? state.tasks.map((task) => `<article class="history-row"><div class="history-main"><strong>${escapeHtml(task.entry_name || task.entry)} · ${shortTaskId(task.task_id)}</strong><small>${formatDateTime(task.start_time)}${task.retry_of ? " · 重试任务" : ""}</small></div><span class="history-status ${statusClass(task.status)}">${escapeHtml(statusLabels[task.status] || task.status)}</span><span class="history-stat">${Number(task.completed_pages || 0)} / ${Number(task.total_pages || 0)} 文档 · ${formatDuration(task.elapsed_seconds)}</span><div class="row-actions"><button class="text-button" type="button" data-open-task="${escapeAttr(task.task_id)}">查看</button>${["failed", "cancelled"].includes(task.status) ? `<button class="text-button" type="button" data-retry-task="${escapeAttr(task.task_id)}">重试</button>` : ""}</div></article>`).join("") : '<div class="empty-row">暂无历史任务</div>';
        renderDatasets();
        updateActionAvailability();
    }

    function renderDatasets() {
        const completed = state.tasks.filter((task) => task.download_available);
        setVisible($("#datasetEmpty"), completed.length === 0);
        const latest = completed.find((task) => task.task_id === state.taskId) || completed[0];
        setVisible($("#resultPanel"), Boolean(latest));
        if (latest) {
            $("#resultTitle").textContent = `${latest.entry_name}数据集`;
            $("#resultTaskMeta").textContent = `${formatDateTime(latest.end_time)} · 任务 ${shortTaskId(latest.task_id)}`;
            const metrics = latest.metrics || {};
            $("#resultDescription").textContent = `共 ${metrics.documents || latest.completed_pages || 0} 个文档、${metrics.chunks || 0} 个知识分块，质量得分 ${metrics.quality_score ?? "—"}。完整包包含文档、结构化数据和质量报告。`;
            $("#downloadButton").dataset.taskId = latest.task_id;
        }
        $("#datasetList").innerHTML = completed.length ? completed.map((task) => `<article class="dataset-row"><div class="dataset-main"><strong>${escapeHtml(task.entry_name)}数据集</strong><small>任务 ${shortTaskId(task.task_id)} · ${formatDateTime(task.end_time)}</small></div><span class="history-status completed">可下载</span><span class="dataset-stat">${task.metrics?.documents || task.completed_pages || 0} 个文档 · ${task.metrics?.chunks || 0} 个分块</span><div class="row-actions"><button class="text-button" type="button" data-open-task="${escapeAttr(task.task_id)}">详情</button><button class="text-button" type="button" data-download-task="${escapeAttr(task.task_id)}">下载</button></div></article>`).join("") : '<div class="empty-row">暂无可下载数据集</div>';
    }

    function updateTaskUI(task) {
        if (!task) return renderMonitorVisibility();
        const status = task.status || "pending";
        const phase = task.phase || "queued";
        const percent = Math.max(0, Math.min(100, Number(task.progress || 0)));
        const finished = ["completed", "failed", "cancelled"].includes(status);
        setVisible($("#metricStrip"), true);
        setVisible($("#topTaskStatus"), true);
        $("#topTaskStatus strong").textContent = `${task.entry_name || task.entry} · ${statusLabels[status] || status}`;
        $("#topTaskStatus").classList.toggle("is-complete", status === "completed");
        $("#runTitle").textContent = task.entry_name || "任务运行状态";
        $("#runTaskMeta").textContent = `任务 ${shortTaskId(task.task_id)} · ${formatDateTime(task.start_time)}`;
        $("#runStatus").textContent = statusLabels[status] || status;
        $("#runStatus").className = `status-tag ${status === "completed" ? "status-success" : ["failed"].includes(status) ? "status-failed" : status === "cancelled" ? "status-cancelled" : "status-running"}`;
        $("#runMessage").textContent = task.message || "任务处理中…";
        $("#runPercent").textContent = `${percent}%`;
        $("#runProgress").style.width = `${percent}%`;
        $("#runCurrentItem").textContent = task.current_item || phaseLabels[phase] || "等待任务启动";
        $("#runSuccessful").textContent = Number(task.successful_pages || 0);
        $("#runFailed").textContent = Number(task.failed_pages || 0);
        $("#runSkipped").textContent = Number(task.skipped_pages || 0);
        $("#runElapsed").textContent = formatDuration(task.elapsed_seconds);
        renderPipeline(task);
        renderLogs(task.logs || []);
        updateMetrics(task);
        setVisible($("#cancelTaskButton"), ACTIVE_STATUSES.has(status));
        $("#cancelTaskButton").disabled = status === "cancelling";
        setVisible($("#retryTaskButton"), ["failed", "cancelled"].includes(status));
        setVisible($("#monitorDownloadButton"), status === "completed" && task.download_available);
        $("#monitorDownloadButton").dataset.taskId = task.task_id;
        renderMonitorVisibility();
        updateActionAvailability();
        if (finished) renderDatasets();
    }

    function renderPipeline(task) {
        const phaseIndex = phaseOrder.indexOf(task.phase);
        $$(".pipeline-row").forEach((row) => {
            const rowIndex = phaseOrder.indexOf(row.dataset.runPhase);
            const completed = task.status === "completed" || (phaseIndex >= 0 && rowIndex < phaseIndex);
            const active = ACTIVE_STATUSES.has(task.status) && row.dataset.runPhase === task.phase;
            const failed = task.status === "failed" && row.dataset.runPhase === task.phase;
            row.classList.toggle("done", completed);
            row.classList.toggle("active", active);
            row.classList.toggle("failed", failed);
            row.querySelector("em").textContent = completed ? "已完成" : active ? "进行中" : failed ? "失败" : "等待";
        });
    }

    function renderLogs(logs) {
        $("#logCount").textContent = `${logs.length} 条`;
        $("#runLog").textContent = logs.length ? logs.map((log) => `${formatLogTime(log.time)}  ${log.message}`).join("\n") : "任务日志将在这里显示。";
        $("#runLog").scrollTop = $("#runLog").scrollHeight;
    }

    function updateMetrics(task) {
        const metrics = task.metrics || {};
        const documents = metrics.documents || (task.status === "completed" ? task.completed_pages : task.total_pages);
        $("#metricDocuments").textContent = documents || "—";
        $("#metricDocumentsHint").textContent = task.status === "completed" ? `${metrics.empty_documents || 0} 个空内容` : `${task.completed_pages || 0} 个已处理`;
        $("#metricQuality").textContent = metrics.quality_score == null ? "—" : metrics.quality_score;
        $("#metricQualityHint").textContent = metrics.quality_score == null ? "完成检查后更新" : "满分 100";
        $("#metricIssues").textContent = metrics.errors == null && metrics.warnings == null ? "—" : Number(metrics.errors || 0) + Number(metrics.warnings || 0);
        $("#metricIssuesHint").textContent = `${metrics.errors || 0} 个错误 · ${metrics.warnings || 0} 个警告`;
        $("#metricChunks").textContent = metrics.chunks || "—";
        $("#metricChunksHint").textContent = metrics.categories ? `${metrics.categories} 个分类` : "生成数据集后可见";
    }

    function renderMonitorVisibility() {
        const hasTask = Boolean(state.task);
        setVisible($("#runEmpty"), !hasTask);
        setVisible($("#runPanel"), hasTask);
    }

    function updateActionAvailability() {
        const busy = Boolean(activeTask());
        $("#startButton").disabled = busy;
        $("#startSelectedButton").disabled = busy;
        $("#newTaskButton").disabled = busy;
    }

    async function cancelCurrentTask() {
        if (!state.taskId || !state.task || !ACTIVE_STATUSES.has(state.task.status)) return;
        if (!window.confirm("确定取消当前任务吗？系统会在安全检查点停止。")) return;
        $("#cancelTaskButton").disabled = true;
        try {
            const data = await request(`/tasks/${state.taskId}/cancel`, { method: "POST" });
            notify(data.message, "warning");
            startPolling();
        } catch (error) {
            notify(`取消失败：${error.message}`, "error", { retry: cancelCurrentTask });
        }
    }

    async function retryTask(taskId) {
        if (activeTask()) {
            notify("已有任务正在处理，暂时无法重试。", "warning", { persistent: true });
            return;
        }
        try {
            const data = await request(`/tasks/${taskId}/retry`, { method: "POST" });
            state.taskId = data.task_id;
            window.localStorage.setItem(STORAGE_TASK_KEY, data.task_id);
            await fetchTask(data.task_id);
            await loadTasks({ preserveCurrent: true });
            showView("monitor");
            startPolling();
            notify(data.message || "已创建重试任务", "success");
        } catch (error) {
            notify(`重试失败：${error.message}`, "error", { retry: () => retryTask(taskId) });
        }
    }

    function retryCurrentTask() {
        if (state.taskId) retryTask(state.taskId);
    }

    async function selectTask(taskId, view = "monitor") {
        state.taskId = taskId;
        window.localStorage.setItem(STORAGE_TASK_KEY, taskId);
        const task = await fetchTask(taskId, { notifyError: true });
        if (task && ACTIVE_STATUSES.has(task.status)) startPolling();
        showView(view);
    }

    function createNewTask() {
        const running = activeTask();
        if (running) {
            selectTask(running.task_id, "monitor");
            notify("当前任务仍在运行，完成或取消后即可新建任务。", "warning", { persistent: true });
            return;
        }
        state.task = null;
        state.taskId = null;
        window.localStorage.removeItem(STORAGE_TASK_KEY);
        setVisible($("#metricStrip"), false);
        setVisible($("#topTaskStatus"), false);
        showView("collect");
        showStage("configure");
        renderMonitorVisibility();
    }

    async function loginShowdoc() {
        const button = $("#loginButton");
        button.disabled = true;
        button.textContent = state.loggedIn ? "正在刷新项目…" : "正在登录…";
        try {
            if (!state.loggedIn) await request("/showdoc/login", { method: "POST", headers: { "Content-Type": "application/json" } });
            await loadShowdocProjects();
            notify(state.loggedIn ? "项目列表已刷新" : "ShowDoc 登录成功", "success");
        } catch (error) {
            state.loggedIn = false;
            setAuthState(false);
            notify(`登录失败：${error.message}`, "error", { retry: loginShowdoc });
        } finally {
            button.disabled = false;
            button.textContent = state.loggedIn ? "刷新项目" : "登录并加载项目";
        }
    }

    function setAuthState(connected) {
        state.loggedIn = connected;
        $("#authDot").classList.toggle("connected", connected);
        $("#authText").textContent = connected ? "已连接，会话可复用" : "尚未登录";
        $("#projectSelect").disabled = !connected;
        $("#loginButton").textContent = connected ? "刷新项目" : "登录并加载项目";
    }

    async function loadShowdocProjects({ silent = false } = {}) {
        const select = $("#projectSelect");
        const savedProject = state.sourceStates.showdoc_account?.projectId || select.value;
        select.innerHTML = '<option value="">项目加载中…</option>';
        try {
            const data = await request("/showdoc/projects");
            select.innerHTML = '<option value="">请选择项目</option>';
            (data.projects || []).forEach((project) => {
                const option = document.createElement("option");
                option.value = project.item_id;
                option.textContent = `${project.item_name}（编号 ${project.item_id}）`;
                select.appendChild(option);
            });
            if (savedProject) select.value = savedProject;
            setAuthState(true);
            return true;
        } catch (error) {
            select.innerHTML = '<option value="">请先登录</option>';
            setAuthState(false);
            if (!silent) throw error;
            return false;
        }
    }

    function previewDefault() {
        if (!validateConfig()) return;
        const pageId = $("#defaultPageId").value.trim();
        if (!pageId) return notify("请先填写默认页编号", "warning");
        showPreview(pageId, `默认页（${pageId}）`, $("#previewDefault"));
    }

    function downloadTask(taskId) {
        if (taskId) window.location.assign(`/download/${taskId}`);
    }

    function formatDuration(value) {
        const seconds = Math.max(0, Number(value || 0));
        if (seconds < 60) return `${seconds} 秒`;
        const minutes = Math.floor(seconds / 60);
        const rest = seconds % 60;
        return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分钟`;
    }

    function formatDate(value) {
        if (!value) return "—";
        return new Date(value).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
    }

    function formatDateTime(value) {
        if (!value) return "—";
        return new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
    }

    function formatLogTime(value) {
        if (!value) return "--:--:--";
        return new Date(value).toLocaleTimeString("zh-CN", { hour12: false });
    }

    function shortTaskId(taskId) { return String(taskId || "").slice(0, 8); }
    function statusClass(status) { return status === "completed" ? "completed" : status === "failed" ? "failed" : status === "cancelled" ? "cancelled" : "running"; }
    function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]); }
    function escapeAttr(value) { return escapeHtml(value).replace(/`/g, "&#96;"); }

    function bindEvents() {
        document.addEventListener("click", (event) => {
            const viewButton = event.target.closest("[data-view]");
            if (viewButton) showView(viewButton.dataset.view);

            const taskButton = event.target.closest("[data-task-id]");
            if (taskButton) selectTask(taskButton.dataset.taskId);

            const openTaskButton = event.target.closest("[data-open-task]");
            if (openTaskButton) selectTask(openTaskButton.dataset.openTask);

            const retryButton = event.target.closest("[data-retry-task]");
            if (retryButton) retryTask(retryButton.dataset.retryTask);

            const downloadButton = event.target.closest("[data-download-task]");
            if (downloadButton) downloadTask(downloadButton.dataset.downloadTask);
        });
        $$(".source-card").forEach((card) => card.addEventListener("click", () => setSource(card.dataset.source)));
        $$(".flow-step[data-step]").forEach((button) => button.addEventListener("click", () => showStage(button.dataset.step)));
        $("#downloadMode").addEventListener("change", () => { updateLoadButton(); captureSourceState(); });
        $("#loadPagesButton").addEventListener("click", loadPages);
        $("#jobForm").addEventListener("submit", (event) => { event.preventDefault(); startJob(); });
        $("#startSelectedButton").addEventListener("click", () => startJob({ useSelection: true }));
        $("#backToConfig").addEventListener("click", () => showStage("configure"));
        $("#pageSearch").addEventListener("input", () => { state.pageNumber = 1; renderRecords(); });
        $("#recordsBody").addEventListener("change", (event) => {
            const checkbox = event.target.closest("input[data-page-id]");
            if (!checkbox) return;
            if (checkbox.checked) state.selectedIds.add(checkbox.dataset.pageId); else state.selectedIds.delete(checkbox.dataset.pageId);
            captureSourceState();
            updateSelectionMeta();
        });
        $("#recordsBody").addEventListener("click", (event) => {
            const button = event.target.closest(".preview-page");
            if (!button) return;
            const page = state.pages.find((item) => String(item.page_id) === button.dataset.pageId);
            if (page) showPreview(page.page_id, page.page_title, button);
        });
        $("#selectVisible").addEventListener("change", (event) => {
            visiblePages().forEach((page) => {
                const id = String(page.page_id);
                if (event.target.checked) state.selectedIds.add(id); else state.selectedIds.delete(id);
            });
            captureSourceState();
            renderRecords();
        });
        $("#selectAllButton").addEventListener("click", () => selectFiltered(true));
        $("#clearSelectionButton").addEventListener("click", () => selectFiltered(false));
        $("#prevPage").addEventListener("click", () => { state.pageNumber -= 1; renderRecords(); });
        $("#nextPage").addEventListener("click", () => { state.pageNumber += 1; renderRecords(); });
        $("#loginButton").addEventListener("click", loginShowdoc);
        $("#previewDefault").addEventListener("click", previewDefault);
        $("#closePreview").addEventListener("click", closePreview);
        $("#previewModal").addEventListener("click", (event) => { if (event.target === $("#previewModal")) closePreview(); });
        document.addEventListener("keydown", trapModalFocus);
        $("#cancelTaskButton").addEventListener("click", cancelCurrentTask);
        $("#retryTaskButton").addEventListener("click", retryCurrentTask);
        $("#monitorDownloadButton").addEventListener("click", (event) => downloadTask(event.currentTarget.dataset.taskId));
        $("#downloadButton").addEventListener("click", (event) => downloadTask(event.currentTarget.dataset.taskId));
        $("#topTaskStatus").addEventListener("click", () => showView("monitor"));
        $("#newTaskButton").addEventListener("click", createNewTask);
        $("#refreshTasks").addEventListener("click", () => loadTasks({ preserveCurrent: true }));
        $("#historyRefresh").addEventListener("click", () => loadTasks({ preserveCurrent: true }));
        ["itemId", "projectSelect", "webUrl"].forEach((id) => $("#" + id).addEventListener("input", () => { $("#" + id).removeAttribute("aria-invalid"); clearValidation(); }));
        window.setInterval(() => {
            updateClock();
            if (state.task && ACTIVE_STATUSES.has(state.task.status)) {
                state.task.elapsed_seconds = Math.floor((Date.now() - new Date(state.task.start_time).getTime()) / 1000);
                $("#runElapsed").textContent = formatDuration(state.task.elapsed_seconds);
            }
        }, 1000);
    }

    document.addEventListener("DOMContentLoaded", async () => {
        bindEvents();
        setSource(state.source, { initial: true });
        updateClock();
        renderMonitorVisibility();
        await loadTasks();
    });
})();
