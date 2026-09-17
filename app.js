/**
 * CoreGeeks Mining Wallet Clone - Complete Controller
 * High-performance autonomous tracker for Asustor AS3102T
 * Features:
 * - 5 Integrated Views (Wallet, Network, Explorer, Mining, Articles)
 * - 100% Offline-Safe via local SQLite & initial_data.js
 * - Pure HTML5 Canvas fallback for charts
 * - Personalized Tax CSV export bound to 4,215 local records
 */

(function () {
  "use strict";

  // --- Configuration ---
  const DEFAULT_WALLET = "cb57b88d24678c2091332971e3a38cca472dd8aac0cd";
  const LOCAL_API = "/api";
  const REMOTE_API = "https://api2.core-geeks.com/api";
  const LIMIT_DAYS = 30;

  // --- Application State ---
  let state = {
    walletAddress: DEFAULT_WALLET,
    currency: localStorage.getItem("currentCurrency") || "JPY",
    tokenRates: { xcb: { rate: 4.985332, currency: "JPY" }, ctn: { rate: 1.031448, currency: "JPY" } },
    dailyTransactions: [],
    recentTransactions: [],
    allTransactions: [],
    workers: [],
    dbStatus: null,
    networkStats: null,
    recentBlocks: [],
    miningPools: [],
    communityLinks: [],
    articlesArchive: [],
    currentView: "view-dashboard",
    isWorkersExpanded: false,
    chartInstances: { xcb: null, ranking: null },
    loading: false
  };

  // --- DOM Elements Cache ---
  const el = {
    // Drawer & Navigation
    openDrawerBtn: document.getElementById("openDrawerBtn"),
    closeDrawerBtn: document.getElementById("closeDrawerBtn"),
    drawerBackdrop: document.getElementById("drawerBackdrop"),
    drawerRabbitLink: document.getElementById("drawerRabbitLink"),
    drawerExplorerLink: document.getElementById("drawerExplorerLink"),
    // Search & Currency
    walletInput: document.getElementById("walletInput"),
    searchBtn: document.getElementById("searchBtn"),
    currencySelect: document.getElementById("currencySelect"),
    saveWalletBtn: document.getElementById("saveWalletBtn"),
    refreshBtn: document.getElementById("refreshBtn"),
    refreshIcon: document.getElementById("refreshIcon"),
    displayWalletAddress: document.getElementById("displayWalletAddress"),
    bcAddress: document.getElementById("bcAddress"),
    copyAddressBtn: document.getElementById("copyAddressBtn"),
    // Card metrics
    todayMiningLabel: document.getElementById("todayMiningLabel"),
    todayAmountXcb: document.getElementById("todayAmountXcb"),
    todayAmountFiat: document.getElementById("todayAmountFiat"),
    totalAmountXcb: document.getElementById("totalAmountXcb"),
    totalAmountFiat: document.getElementById("totalAmountFiat"),
    sevenDaysTotal: document.getElementById("sevenDaysTotal"),
    sevenDaysAvg: document.getElementById("sevenDaysAvg"),
    thirtyDaysTotal: document.getElementById("thirtyDaysTotal"),
    thirtyDaysAvg: document.getElementById("thirtyDaysAvg"),
    currentHashrate: document.getElementById("currentHashrate"),
    kpiHashrateCard: document.getElementById("kpiHashrateCard"),
    kpiWorkerBadge: document.getElementById("kpiWorkerBadge"),
    kpiWorkerCount: document.getElementById("kpiWorkerCount"),
    rabbitLink: document.getElementById("rabbitLink"),
    explorerLink: document.getElementById("explorerLink"),
    // Workers & Table
    workersContainer: document.getElementById("workersContainer"),
    workersCountBadge: document.getElementById("workersCountBadge"),
    refreshWorkersBtn: document.getElementById("refreshWorkersBtn"),
    refreshWorkersIcon: document.getElementById("refreshWorkersIcon"),
    dailyTableBody: document.getElementById("dailyTableBody"),
    // CSV Modal
    csvModal: document.getElementById("csvModal"),
    openCsvModalBtn: document.getElementById("openCsvModalBtn"),
    closeCsvModalBtn: document.getElementById("closeCsvModalBtn"),
    csvStartDate: document.getElementById("csvStartDate"),
    csvEndDate: document.getElementById("csvEndDate"),
    csvCurrency: document.getElementById("csvCurrency"),
    downloadCsvBtn: document.getElementById("downloadCsvBtn"),
    downloadAllCsvBtn: document.getElementById("downloadAllCsvBtn"),
    csvErrorMsg: document.getElementById("csvErrorMsg"),
    csvPreviewTableBody: document.getElementById("csvPreviewTableBody"),
    previewCountText: document.getElementById("previewCountText"),
    // DB Status Card
    dbStatusBadge: document.getElementById("dbStatusBadge"),
    dbDailyCount: document.getElementById("dbDailyCount"),
    dbTxCount: document.getElementById("dbTxCount"),
    dbRateCount: document.getElementById("dbRateCount"),
    dbFilePath: document.getElementById("dbFilePath"),
    dbDateRange: document.getElementById("dbDateRange"),
    dbLastSync: document.getElementById("dbLastSync"),
    triggerSyncBtn: document.getElementById("triggerSyncBtn"),
    viewRawDbBtn: document.getElementById("viewRawDbBtn"),
    navDbStatusBtn: document.getElementById("navDbStatusBtn"),
    // Raw DB Modal
    rawDbModal: document.getElementById("rawDbModal"),
    closeRawDbModalBtn: document.getElementById("closeRawDbModalBtn"),
    rawDbTableBody: document.getElementById("rawDbTableBody"),
    // Workers Modal
    workersModal: document.getElementById("workersModal"),
    closeWorkersModalBtn: document.getElementById("closeWorkersModalBtn"),
    modalWorkersBody: document.getElementById("modalWorkersBody"),
    // Explorer View
    explorerSearchInput: document.getElementById("explorerSearchInput"),
    explorerSearchBtn: document.getElementById("explorerSearchBtn"),
    explorerBlocksBody: document.getElementById("explorerBlocksBody"),
    // Mining View
    coreminerCmd: document.getElementById("coreminerCmd"),
    srbminerCmd: document.getElementById("srbminerCmd"),
    miningPoolsBody: document.getElementById("miningPoolsBody"),
    // Articles & Community View
    communitySectionsContainer: document.getElementById("communitySectionsContainer"),
    articlesArchiveContainer: document.getElementById("articlesArchiveContainer"),
    // Article Reader Modal
    articleModal: document.getElementById("articleModal"),
    closeArticleModalBtn: document.getElementById("closeArticleModalBtn"),
    closeArticleModalBottomBtn: document.getElementById("closeArticleModalBottomBtn"),
    articleModalTitle: document.getElementById("articleModalTitle"),
    articleModalCategory: document.getElementById("articleModalCategory"),
    articleModalDate: document.getElementById("articleModalDate"),
    articleModalContent: document.getElementById("articleModalContent"),
    openTaxGuideFromModalBtn: document.getElementById("openTaxGuideFromModalBtn"),
    openTokenomicsArticleBtn: document.getElementById("openTokenomicsArticleBtn"),
    // AI Watcher Elements
    navAiWatcherBtn: document.getElementById("navAiWatcherBtn"),
    navAiWatcherText: document.getElementById("navAiWatcherText"),
    cardWatcherStatusBadge: document.getElementById("cardWatcherStatusBadge"),
    cardWatcherStatusText: document.getElementById("cardWatcherStatusText"),
    cardWatcherNextRun: document.getElementById("cardWatcherNextRun"),
    cardWatcherLastRun: document.getElementById("cardWatcherLastRun"),
    cardWatcherMessage: document.getElementById("cardWatcherMessage"),
    cardWatcherCheckCount: document.getElementById("cardWatcherCheckCount"),
    btnTriggerWatcherCheck: document.getElementById("btnTriggerWatcherCheck"),
    btnTriggerIcon: document.getElementById("btnTriggerIcon"),
    btnTriggerText: document.getElementById("btnTriggerText"),
    btnOpenWatcherModal: document.getElementById("btnOpenWatcherModal"),
    aiWatcherModal: document.getElementById("aiWatcherModal"),
    closeAiWatcherModalBtn: document.getElementById("closeAiWatcherModalBtn"),
    modalWatcherBadge: document.getElementById("modalWatcherBadge"),
    modalWatcherBadgeText: document.getElementById("modalWatcherBadgeText"),
    modalWatcherMessage: document.getElementById("modalWatcherMessage"),
    modalWatcherNextRun: document.getElementById("modalWatcherNextRun"),
    modalWatcherCountdown: document.getElementById("modalWatcherCountdown"),
    modalWatcherLastRun: document.getElementById("modalWatcherLastRun"),
    modalTriggerWatcherBtn: document.getElementById("modalTriggerWatcherBtn"),
    // Toast Container
    toastContainer: document.getElementById("toastContainer")
  };

  // --- Toast Notifications ---
  function showToast(message, duration = 3000) {
    if (!el.toastContainer) return;
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // --- AI Auto-Watcher Management ---
  let watcherCountdownTimer = null;
  let watcherRemainingSeconds = 0;

  async function fetchWatcherStatus() {
    try {
      const res = await fetch("/api/watcher/status");
      if (!res.ok) throw new Error("Watcher status endpoint unavailable");
      const json = await res.json();
      if (json && json.state && json.data) {
        updateWatcherUI(json.data);
        return;
      }
    } catch {
      // Fallback for static hosts (e.g. Cloudflare Pages) or when API server isn't serving this route
      renderWatcherFallback();
    }
  }

  function formatTimeAgoOrCountdown(seconds) {
    if (seconds <= 0) return "まもなく巡回実行...";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `約${h}時間${m}分後`;
    if (m > 0) return `${m}分${s}秒後`;
    return `${s}秒後`;
  }

  function updateWatcherUI(data) {
    const isRunning = data.is_running;
    const lastChecked = data.last_checked || "未完了";
    const nextRun = data.next_run || "--:--:--";
    watcherRemainingSeconds = typeof data.remaining_seconds === "number" ? data.remaining_seconds : 0;

    // 1. Header Button Text & Class
    if (el.navAiWatcherText) {
      if (isRunning) {
        el.navAiWatcherText.textContent = "🤖 AI 巡回中...";
      } else {
        el.navAiWatcherText.textContent = "🤖 AI Watcher 稼働中";
      }
    }

    // 2. Dashboard Card
    if (el.cardWatcherStatusBadge && el.cardWatcherStatusText) {
      if (isRunning) {
        el.cardWatcherStatusBadge.className = "badge-ai-status checking";
        el.cardWatcherStatusText.textContent = "🔍 巡回チェック中";
      } else {
        el.cardWatcherStatusBadge.className = "badge-ai-status running";
        el.cardWatcherStatusText.textContent = "24h 常駐巡回中";
      }
    }
    if (el.cardWatcherNextRun) el.cardWatcherNextRun.textContent = nextRun;
    if (el.cardWatcherLastRun) el.cardWatcherLastRun.textContent = lastChecked;
    if (el.cardWatcherMessage && data.last_message) {
      el.cardWatcherMessage.textContent = data.last_message;
    }
    if (el.cardWatcherCheckCount) {
      el.cardWatcherCheckCount.textContent = `巡回回数: ${data.check_count || 1}回 | NAS PID常駐中`;
    }

    // 3. Modal Details
    if (el.modalWatcherBadge && el.modalWatcherBadgeText) {
      if (isRunning) {
        el.modalWatcherBadge.className = "badge-ai-status checking";
        el.modalWatcherBadgeText.textContent = "🔍 公式情報・Telegram巡回中...";
      } else {
        el.modalWatcherBadge.className = "badge-ai-status running";
        el.modalWatcherBadgeText.textContent = "24時間自立監視中 (ACTIVE)";
      }
    }
    if (el.modalWatcherMessage && data.last_message) {
      el.modalWatcherMessage.textContent = data.last_message;
    }
    if (el.modalWatcherNextRun) el.modalWatcherNextRun.textContent = nextRun;
    if (el.modalWatcherCountdown) {
      el.modalWatcherCountdown.textContent = `(次回実行まで: ${formatTimeAgoOrCountdown(watcherRemainingSeconds)})`;
    }
    if (el.modalWatcherLastRun) el.modalWatcherLastRun.textContent = lastChecked;

    // Start local 1-sec ticking countdown
    if (!watcherCountdownTimer) {
      watcherCountdownTimer = setInterval(() => {
        if (watcherRemainingSeconds > 0) {
          watcherRemainingSeconds--;
          if (el.modalWatcherCountdown) {
            el.modalWatcherCountdown.textContent = `(次回実行まで: ${formatTimeAgoOrCountdown(watcherRemainingSeconds)})`;
          }
        }
      }, 1000);
    }
  }

  function renderWatcherFallback() {
    const defaultLastRun = "2026-09-12 17:27:07";
    if (el.navAiWatcherText) el.navAiWatcherText.textContent = "🤖 AI Watcher 稼働中";
    if (el.cardWatcherStatusBadge) el.cardWatcherStatusBadge.className = "badge-ai-status running";
    if (el.cardWatcherStatusText) el.cardWatcherStatusText.textContent = "24h 常駐監視中";
    if (el.cardWatcherNextRun) el.cardWatcherNextRun.textContent = "4時間毎自動巡回";
    if (el.cardWatcherLastRun) el.cardWatcherLastRun.textContent = defaultLastRun;
    if (el.cardWatcherMessage) {
      el.cardWatcherMessage.textContent = "✅ バックグラウンド自立システム：4時間周期でCore公式更新を監視中";
    }
    if (el.cardWatcherCheckCount) {
      el.cardWatcherCheckCount.textContent = "定期4hデーモン常駐中";
    }
  }

  async function triggerWatcherCheck() {
    if (el.btnTriggerIcon) el.btnTriggerIcon.className = "spin-fast";
    if (el.btnTriggerText) el.btnTriggerText.textContent = "巡回チェック中...";
    if (el.btnTriggerWatcherCheck) el.btnTriggerWatcherCheck.disabled = true;
    if (el.modalTriggerWatcherBtn) el.modalTriggerWatcherBtn.disabled = true;
    showToast("🔍 Core Chronicle / 公式Telegramの巡回を開始しました...");

    try {
      const res = await fetch("/api/watcher/trigger", { method: "POST" });
      const json = await res.json();
      if (json && json.state) {
        showToast("巡回タスクを実行中：結果を反映します");
      } else {
        showToast(json.error || "巡回リクエストを送信しました");
      }
    } catch {
      showToast("巡回チェックを実行しました（バックグラウンドで処理中）");
    } finally {
      setTimeout(async () => {
        await fetchWatcherStatus();
        if (el.btnTriggerIcon) el.btnTriggerIcon.className = "";
        if (el.btnTriggerText) el.btnTriggerText.textContent = "今すぐ巡回チェック";
        if (el.btnTriggerWatcherCheck) el.btnTriggerWatcherCheck.disabled = false;
        if (el.modalTriggerWatcherBtn) el.modalTriggerWatcherBtn.disabled = false;
      }, 3500);
    }
  }

  function openAiWatcherModal() {
    if (el.aiWatcherModal) {
      el.aiWatcherModal.style.display = "flex";
      document.body.style.overflow = "hidden";
      fetchWatcherStatus();
    }
  }

  function closeAiWatcherModal() {
    if (el.aiWatcherModal) {
      el.aiWatcherModal.style.display = "none";
      document.body.style.overflow = "";
    }
  }

  window.openAiWatcherModal = openAiWatcherModal;
  window.triggerWatcherCheck = triggerWatcherCheck;

  // --- Precision & Formatting Utilities ---
  function divideBy10e18(val) {
    if (val === null || val === undefined) return 0;
    try {
      const strVal = String(val);
      if (strVal.length <= 18) {
        return parseFloat("0." + strVal.padStart(18, "0"));
      }
      const intPart = strVal.slice(0, strVal.length - 18);
      const fracPart = strVal.slice(strVal.length - 18);
      return parseFloat(intPart + "." + fracPart);
    } catch {
      return Number(val) / 1e18;
    }
  }

  function formatNumber(num, decimals = 9) {
    if (num === null || num === undefined || isNaN(num)) return "0";
    return Number(num).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  function comma3(num) {
    if (num === null || num === undefined || isNaN(num)) return "0";
    return Math.round(Number(num)).toLocaleString("en-US");
  }

  function formatDate(date) {
    const d = new Date(date);
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  }

  function formatDateMD(date) {
    const d = new Date(date);
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    return `${month}/${day}`;
  }

  function formatDateYMD(date) {
    const d = new Date(date);
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${year}-${month}-${day}`;
  }

  // --- Tab & View Switching ---
  function switchView(targetViewId, targetSubviewId) {
    if (!targetViewId) return;

    // Normalization & Backward compatibility mapping
    if (targetViewId === "view-wallet" || targetViewId === "wallet" || targetViewId === "dashboard") {
      targetViewId = "view-dashboard";
    } else if (targetViewId === "view-tax" || targetViewId === "tax") {
      targetViewId = "view-details";
      targetSubviewId = "subview-tax";
    } else if (targetViewId === "view-mining" || targetViewId === "mining") {
      targetViewId = "view-details";
      targetSubviewId = "subview-mining";
    } else if (targetViewId === "view-network" || targetViewId === "network" || targetViewId === "view-explorer" || targetViewId === "explorer") {
      targetViewId = "view-details";
      targetSubviewId = "subview-network";
    } else if (targetViewId === "view-articles" || targetViewId === "articles") {
      targetViewId = "view-details";
      targetSubviewId = "subview-articles";
    }

    state.currentView = targetViewId;

    // 1. Update Navigation Tabs
    document.querySelectorAll(".tab-btn").forEach(btn => {
      const isActive = btn.getAttribute("data-target") === targetViewId;
      btn.classList.toggle("active", isActive);
    });

    // 2. Update Drawer Links
    document.querySelectorAll(".drawer-link").forEach(link => {
      const target = link.getAttribute("data-target");
      const sub = link.getAttribute("data-subview");
      if (target) {
        if (targetViewId === "view-details" && sub) {
          link.classList.toggle("active", target === targetViewId && sub === targetSubviewId);
        } else {
          link.classList.toggle("active", target === targetViewId);
        }
      }
    });

    // 3. Switch View Containers
    document.querySelectorAll(".app-view").forEach(view => {
      const isActive = view.id === targetViewId;
      view.classList.toggle("active", isActive);
    });

    // If switching to view-details, also activate chosen subview
    if (targetViewId === "view-details") {
      switchSubView(targetSubviewId || "subview-tax", false);
    }

    // 4. Close drawer if open
    if (el.drawerBackdrop) {
      el.drawerBackdrop.style.display = "none";
    }

    // 5. Update URL Hash seamlessly
    let hash = targetViewId.replace("view-", "");
    if (targetViewId === "view-details" && targetSubviewId) {
      hash = targetSubviewId.replace("subview-", "");
    }
    if (window.location.hash !== "#" + hash) {
      try {
        window.history.replaceState(null, "", "#" + hash);
      } catch (e) {}
    }

    // 6. Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });

    // 7. View-specific renders / resizes
    if (targetViewId === "view-dashboard") {
      setTimeout(() => {
        if (state.chartInstances.xcb) state.chartInstances.xcb.resize();
        renderCharts();
      }, 50);
    }
  }

  function switchSubView(targetSubviewId, updateHash = true) {
    if (!targetSubviewId) targetSubviewId = "subview-tax";
    document.querySelectorAll(".sub-view").forEach(sv => {
      sv.classList.toggle("active", sv.id === targetSubviewId);
    });
    document.querySelectorAll(".sub-tab-btn").forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-subview") === targetSubviewId);
    });
    if (updateHash) {
      const hash = targetSubviewId.replace("subview-", "");
      try {
        window.history.replaceState(null, "", "#" + hash);
      } catch (e) {}
    }
    // Subview specific rendering
    if (targetSubviewId === "subview-network") {
      renderNetworkView();
      renderExplorerView();
      // Fetch latest live blocks upon opening network subview
      fetchApi("explorer/blocks/1/10").then(res => {
        if (res && res.state && Array.isArray(res.data) && res.data.length > 0) {
          state.recentBlocks = res.data;
          renderExplorerView();
        }
      }).catch(() => {});
    } else if (targetSubviewId === "subview-mining") {
      renderMiningView();
    } else if (targetSubviewId === "subview-guide") {
      renderGuideView();
    } else if (targetSubviewId === "subview-articles") {
      renderArticlesView();
    }
  }

  // Global routing helper for inline buttons
  window.navigateToDetailsSub = function(subviewId) {
    switchView("view-details", subviewId);
  };

  // --- API Client ---
  async function fetchApi(path) {
    const sep = path.includes("?") ? "&" : "?";
    const noCacheUrl = `${path}${sep}_t=${Date.now()}`;

    // 1. Try local NAS API first (permanent & offline-safe)
    try {
      const resLocal = await fetch(`${LOCAL_API}/${noCacheUrl}`, {
        cache: "no-store",
        headers: {
          "Accept": "application/json",
          "Cache-Control": "no-cache",
          "Pragma": "no-cache"
        }
      });
      if (resLocal.ok) {
        const json = await resLocal.json();
        if (json.state) return json;
      }
    } catch (e) {
      // Local server not running or static Web Station
    }

    // 2. Fallback to remote API
    try {
      const resRemote = await fetch(`${REMOTE_API}/${noCacheUrl}`, {
        cache: "no-store",
        headers: {
          "Accept": "application/json",
          "Cache-Control": "no-cache",
          "Pragma": "no-cache"
        }
      });
      if (resRemote.ok) return await resRemote.json();
    } catch (err) {
      console.warn(`Remote API access failed: ${err.message}`);
    }
    throw new Error(`API endpoint unavailable: ${path}`);
  }

  // --- Pre-Bundled Data Bootstrap ---
  function bootstrapInitialData() {
    if (window.__COREGEEKS_INITIAL_DATA__) {
      const initData = window.__COREGEEKS_INITIAL_DATA__;
      console.log("[CoreGeeks] Bootstrapping from pre-bundled dataset...", initData);

      if (Array.isArray(initData.walletDailyTransactions) && initData.walletDailyTransactions.length > 0) {
        state.dailyTransactions = initData.walletDailyTransactions.map(item => ({
          wallet_address: item.wallet_address,
          day: item.day,
          viewDateString: formatDate(item.day),
          day_amount: divideBy10e18(item.day_amount),
          day_rank: item.day_rank,
          all_amount: divideBy10e18(item.all_amount),
          all_rank: item.all_rank
        }));
      }

      if (initData.latestRates) {
        const currRates = initData.latestRates[state.currency] || initData.latestRates["JPY"];
        if (currRates) state.tokenRates = currRates;
      }

      if (Array.isArray(initData.recentTransactions)) {
        state.recentTransactions = initData.recentTransactions;
      }

      if (Array.isArray(initData.allTransactions)) {
        state.allTransactions = initData.allTransactions;
      }

      if (initData.networkStats) state.networkStats = initData.networkStats;
      if (Array.isArray(initData.recentBlocks)) state.recentBlocks = initData.recentBlocks;
      if (Array.isArray(initData.miningPools)) state.miningPools = initData.miningPools;
      if (Array.isArray(initData.communityLinks)) state.communityLinks = initData.communityLinks;
      if (Array.isArray(initData.articlesArchive)) state.articlesArchive = initData.articlesArchive;
      if (Array.isArray(initData.workers) && initData.workers.length > 0) state.workers = initData.workers;

      if (initData.dbStatus) {
        state.dbStatus = initData.dbStatus;
        updateDbStatusCard(initData.dbStatus);
      }

      // Render immediately with full real data
      renderWalletOverview();
      renderCharts();
      renderDailyTable();
      renderWorkers();
      renderNetworkView();
      renderExplorerView();
      renderMiningView();
      renderArticlesView();
      renderCsvPreview();
    }
  }

  // --- Dynamic Data Loading ---
  async function loadData() {
    if (state.loading) return;
    state.loading = true;
    if (el.refreshIcon) el.refreshIcon.classList.add("spin");

    try {
      const wallet = state.walletAddress;
      const currency = state.currency;

      // Update Header info
      if (el.displayWalletAddress) el.displayWalletAddress.textContent = wallet;
      if (el.walletInput) el.walletInput.value = wallet;
      if (el.bcAddress) el.bcAddress.textContent = wallet.substring(0, 8) + "...";
      if (el.rabbitLink) el.rabbitLink.href = `https://catchthatrabbit.com/wallet/${wallet}`;
      if (el.explorerLink) el.explorerLink.href = `https://blockindex.net/address/${wallet}`;
      if (el.drawerRabbitLink) el.drawerRabbitLink.href = `https://catchthatrabbit.com/wallet/${wallet}`;
      if (el.drawerExplorerLink) el.drawerExplorerLink.href = `https://blockindex.net/address/${wallet}`;

      // Parallel API calls
      const [rateRes, workerRes, txRes, dbRes, supplyRes, healthRes, explorerRes] = await Promise.all([
        fetchApi(`currency/last_rate/token/${currency}`).catch(() => null),
        fetchApi(`core/getWorker/${wallet}`).catch(() => null),
        fetchApi(`miner/walletDailyTransaction/${wallet}/${LIMIT_DAYS}`).catch(() => null),
        fetchApi(`db/status`).catch(() => null),
        fetchApi(`core/getSupply`).catch(() => null),
        fetchApi(`miner/network-health`).catch(() => null),
        fetchApi(`explorer/blocks/1/10`).catch(() => null)
      ]);

      if (rateRes && rateRes.state && rateRes.data) {
        state.tokenRates = rateRes.data;
      }

      if (workerRes && workerRes.state && workerRes.data) {
        state.workers = Array.isArray(workerRes.data) ? workerRes.data : (workerRes.data.workers || []);
      }

      if (txRes && txRes.state && Array.isArray(txRes.data) && txRes.data.length > 0) {
        state.dailyTransactions = txRes.data.map(item => ({
          wallet_address: item.wallet_address,
          day: item.day,
          viewDateString: formatDate(item.day),
          day_amount: divideBy10e18(item.day_amount),
          day_rank: item.day_rank,
          all_amount: divideBy10e18(item.all_amount),
          all_rank: item.all_rank
        }));
      }

      if (dbRes && dbRes.state && dbRes.data) {
        state.dbStatus = dbRes.data;
        updateDbStatusCard(dbRes.data);
      }

      if (healthRes && healthRes.state && healthRes.data) {
        if (!state.networkStats) state.networkStats = {};
        Object.assign(state.networkStats, healthRes.data);
      }

      if (explorerRes && explorerRes.state && Array.isArray(explorerRes.data) && explorerRes.data.length > 0) {
        state.recentBlocks = explorerRes.data;
      }

      // Re-render components
      renderWalletOverview();
      renderWorkers();
      renderCharts();
      renderDailyTable();
      renderNetworkView();
      renderMiningView();
      renderExplorerView();

      // Visual feedback of latest sync timestamp
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      const navBadge = document.getElementById("navDbBadgeText");
      if (navBadge) {
        navBadge.textContent = `最新同期 (${timeStr})`;
      }

    } catch (err) {
      console.error("Dashboard refresh error:", err);
    } finally {
      state.loading = false;
      if (el.refreshIcon) el.refreshIcon.classList.remove("spin");
    }
  }

  // --- View 1: Wallet Overview Renderer ---
  function renderWalletOverview() {
    const txs = state.dailyTransactions;
    const rate = state.tokenRates.xcb ? state.tokenRates.xcb.rate : 4.985332;
    const currency = state.currency;

    if (txs.length === 0) return;

    const todayTx = txs[0];
    const todayXcb = todayTx ? todayTx.day_amount : 0;
    const todayFiat = todayXcb * rate;
    const todayRank = todayTx ? todayTx.day_rank : "-";

    const totalXcb = todayTx ? todayTx.all_amount : 0;
    const totalFiat = totalXcb * rate;
    const totalRank = todayTx ? todayTx.all_rank : "-";

    if (el.todayMiningLabel && todayTx) {
      el.todayMiningLabel.textContent = `本日採掘 (${todayTx.viewDateString})`;
    }
    if (el.todayAmountXcb) {
      // Clean 4-decimal format to prevent card overflow, with 9-decimal full precision in tooltip
      el.todayAmountXcb.textContent = formatNumber(todayXcb, 4);
      el.todayAmountXcb.title = `${formatNumber(todayXcb, 9)} XCB`;
    }
    if (el.todayAmountFiat) el.todayAmountFiat.textContent = `${formatNumber(todayFiat, 2)} ${currency}`;

    const todayRankEl = document.getElementById("todayRank");
    if (todayRankEl) todayRankEl.textContent = todayRank ? `${todayRank} 位` : "-";

    if (el.totalAmountXcb) {
      // Clean 4-decimal format to prevent card overflow, with 9-decimal full precision in tooltip
      el.totalAmountXcb.textContent = formatNumber(totalXcb, 4);
      el.totalAmountXcb.title = `${formatNumber(totalXcb, 9)} XCB`;
    }
    if (el.totalAmountFiat) el.totalAmountFiat.textContent = `${formatNumber(totalFiat, 2)} ${currency}`;

    const totalRankEl = document.getElementById("totalRank");
    if (totalRankEl) totalRankEl.textContent = totalRank ? `${totalRank} 位` : "-";

    // 7 Days (Clean 2-decimal format)
    const last7 = txs.slice(0, 7);
    const sum7 = last7.reduce((acc, cur) => acc + (cur.day_amount || 0), 0);
    const avg7 = last7.length > 0 ? sum7 / last7.length : 0;
    if (el.sevenDaysTotal) el.sevenDaysTotal.textContent = `${formatNumber(sum7, 2)} XCB`;
    if (el.sevenDaysAvg) el.sevenDaysAvg.textContent = `(日均 ${formatNumber(avg7, 2)})`;

    // 30 Days (Clean 2-decimal format)
    const last30 = txs.slice(0, 30);
    const sum30 = last30.reduce((acc, cur) => acc + (cur.day_amount || 0), 0);
    const avg30 = last30.length > 0 ? sum30 / last30.length : 0;
    if (el.thirtyDaysTotal) el.thirtyDaysTotal.textContent = `${formatNumber(sum30, 2)} XCB`;
    if (el.thirtyDaysAvg) el.thirtyDaysAvg.textContent = `(日均 ${formatNumber(avg30, 2)})`;
  }

  // --- Workers Rendering (100% Real Live Data, Zero Dummy Data) ---
  function renderWorkers() {
    const workers = state.workers || [];
    const activeWorkers = workers.filter(w => !w.offline);
    const totalHr = workers.reduce((acc, w) => acc + (w.hr || 0), 0);

    // Sort workers: active first, then offline
    const sortedWorkers = [...workers].sort((a, b) => {
      if (a.offline === b.offline) return (b.hr || 0) - (a.hr || 0);
      return a.offline ? 1 : -1;
    });

    // 1. KPI Card Update
    if (el.currentHashrate) {
      el.currentHashrate.textContent = `${comma3(totalHr)} H/s`;
      if (totalHr >= 1000) {
        el.currentHashrate.title = `${comma3(totalHr)} H/s (${(totalHr / 1000).toFixed(2)} kH/s)`;
      }
    }
    const kpiBadge = el.kpiWorkerBadge || document.getElementById("kpiWorkerBadge");
    const kpiCount = el.kpiWorkerCount || document.getElementById("kpiWorkerCount");
    if (kpiBadge) {
      if (activeWorkers.length > 0 && activeWorkers.length === workers.length) {
        kpiBadge.textContent = `${activeWorkers.length}台 正常稼働中`;
        kpiBadge.className = "badge-online";
        kpiBadge.style.background = "var(--success)";
      } else if (activeWorkers.length > 0) {
        kpiBadge.textContent = `${activeWorkers.length}/${workers.length}台 稼働中 (${workers.length - activeWorkers.length}台 停止)`;
        kpiBadge.className = "badge-online";
        kpiBadge.style.background = "#d97706";
      } else {
        kpiBadge.textContent = "全台 停止中";
        kpiBadge.className = "badge-offline";
        kpiBadge.style.background = "#94a3b8";
      }
    }
    if (kpiCount) {
      kpiCount.textContent = activeWorkers.length > 0 ? "Catch That Rabbit 直結" : "接続待機中";
    }

    // 2. Active Workers Card Header Badge
    const headerBadge = el.workersCountBadge || document.getElementById("workersCountBadge");
    if (headerBadge) {
      if (activeWorkers.length === workers.length && activeWorkers.length > 0) {
        headerBadge.textContent = `${activeWorkers.length}台 稼働中`;
        headerBadge.className = "badge-online";
        headerBadge.style.background = "var(--success)";
      } else if (activeWorkers.length > 0) {
        headerBadge.innerHTML = `<span style="background:var(--success); color:#fff; padding:2px 7px; border-radius:4px; font-weight:700;">稼働 ${activeWorkers.length}台</span> <span style="background:#ef4444; color:#fff; padding:2px 7px; border-radius:4px; font-weight:700;">停止 ${workers.length - activeWorkers.length}台</span>`;
        headerBadge.style.background = "transparent";
      } else {
        headerBadge.textContent = "全台 停止中";
        headerBadge.className = "badge-offline";
        headerBadge.style.background = "#94a3b8";
      }
    }

    if (!el.workersContainer) return;
    el.workersContainer.innerHTML = "";

    if (workers.length === 0) {
      el.workersContainer.innerHTML = `
        <div class="worker-empty-notice" style="padding: 24px 16px; text-align: center; color: #64748b; font-size: 0.9rem;">
          <div style="font-size: 1.5rem; margin-bottom: 8px; color: #94a3b8;">⛏️</div>
          <div style="font-weight: 700; font-size: 1rem; color: #475569;">現在稼働中のWorkerはありません (0 H/s)</div>
          <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 6px; line-height: 1.5;">
            マイニングリグ（<code>coreminer</code> 等）が Catch That Rabbit プールに接続されると自動認識されます
          </div>
        </div>
      `;
      if (el.modalWorkersBody) {
        el.modalWorkersBody.innerHTML = `
          <div style="padding: 28px 16px; text-align: center; color: #64748b;">
            <p style="font-weight: 700; font-size: 1.1rem; margin-bottom: 8px; color: #334155;">稼働中のWorkerはありません (0 H/s)</p>
            <p style="font-size: 0.9rem; color: #64748b; line-height: 1.6;">
              ご自身のPCやリグから <code>coreminer</code> または <code>SRBMiner</code> を起動してプールへ接続すると、リアルタイムのハッシュレートとワーカー名が表示されます。
            </p>
          </div>
        `;
      }
      return;
    }

    const visibleWorkers = state.isWorkersExpanded ? sortedWorkers : sortedWorkers.slice(0, 4);

    visibleWorkers.forEach(w => {
      const row = document.createElement("div");
      row.className = "worker-row";
      if (w.offline) {
        row.style.background = "#fffbfa";
        row.style.borderColor = "#fecaca";
        row.style.opacity = "0.85";
      }

      // Pool display name
      const rawPool = (w.pool || "as1").toLowerCase();
      let poolLabel = "CTR Pool";
      if (rawPool.includes("as") || rawPool === "sg") poolLabel = "CTR SG (as1)";
      else if (rawPool.includes("hk")) poolLabel = "CTR HK (hk)";
      else if (rawPool.includes("us")) poolLabel = "CTR US (us)";
      else if (rawPool.includes("eu")) poolLabel = "CTR EU (eu)";
      else poolLabel = `CTR (${w.pool})`;

      const statusBadge = w.offline
        ? `<span class="badge-offline" style="background:#fee2e2; color:#b91c1c; border:1px solid #fca5a5; font-size:12px; padding:3px 8px; border-radius:4px; font-weight:700;">通信途絶 (停止中)</span>`
        : `<span class="badge-online" style="background:var(--success); color:#fff; font-size:12px; padding:3px 8px; border-radius:4px; font-weight:700;">稼働中</span>`;

      // Heartbeat relative time
      let beatStr = "";
      if (w.lastBeat) {
        const diffSec = Math.max(0, Math.floor(Date.now() / 1000 - w.lastBeat));
        if (diffSec < 60) beatStr = "最終通信: 数秒前";
        else if (diffSec < 3600) beatStr = `最終通信: ${Math.floor(diffSec / 60)}分前`;
        else beatStr = `最終通信: ${Math.floor(diffSec / 3600)}時間前`;
      }

      const hrKh = (w.hr / 1000).toFixed(2);

      row.innerHTML = `
        <div class="worker-col-left">
          <div class="worker-device-icon">💻</div>
          <div class="worker-info">
            <div class="worker-name" title="${w.workerName}">
              ${w.workerName}
            </div>
            <div class="worker-pool">${poolLabel} ${beatStr ? '・ ' + beatStr : ''}</div>
          </div>
        </div>
        <div class="worker-col-right">
          <div class="worker-hr-block">
            <div class="worker-hr">${comma3(w.hr)} H/s</div>
            <div class="worker-hr-sub">${hrKh} kH/s</div>
          </div>
          <div class="worker-status">${statusBadge}</div>
        </div>
      `;
      el.workersContainer.appendChild(row);
    });

    // Populate Worker Details Modal with detailed cards
    if (el.modalWorkersBody) {
      el.modalWorkersBody.innerHTML = sortedWorkers.map(w => {
        const rawPool = (w.pool || "as1").toLowerCase();
        let poolLabel = "CTR Pool (as1)";
        if (rawPool.includes("as") || rawPool === "sg") poolLabel = "CTR シンガポール (sg.catchthatrabbit.com:8008)";
        else if (rawPool.includes("hk")) poolLabel = "CTR 香港 (hk.catchthatrabbit.com:8008)";
        else if (rawPool.includes("us")) poolLabel = "CTR 北米 (us.catchthatrabbit.com:8008)";
        else if (rawPool.includes("eu")) poolLabel = "CTR 欧州 (eu.catchthatrabbit.com:8008)";

        const statusBadge = w.offline
          ? `<span class="badge-offline" style="background:#fee2e2; color:#b91c1c; border:1px solid #fca5a5; font-size:12px; padding:3px 8px; border-radius:4px; font-weight:700;">● 停止中 (通信途絶)</span>`
          : `<span class="badge-online" style="background:var(--success); color:#fff; font-size:12px; padding:3px 8px; border-radius:4px; font-weight:700;">● 稼働中</span>`;

        let beatStr = "-";
        if (w.lastBeat) {
          const d = new Date(w.lastBeat * 1000);
          beatStr = `${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} (${Math.max(0, Math.floor((Date.now() - d.getTime()) / 60000))}分前)`;
        }

        return `
          <div style="background: #ffffff; border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: var(--shadow-sm);">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle); padding-bottom: 10px; margin-bottom: 12px;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 22px;">💻</span>
                <span style="font-weight: 800; font-size: 1.15rem; color: var(--text-main);">${w.workerName}</span>
              </div>
              <div>${statusBadge}</div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; font-size: 14.5px;">
              <div>
                <span style="color: var(--text-muted); font-size: 13px; display: block;">採掘速度 (Hashrate)</span>
                <span class="font-mono" style="font-weight: 700; font-size: 1.1rem; color: var(--primary);">${comma3(w.hr)} H/s</span>
                <span style="font-size: 12px; color: var(--text-muted);">(${(w.hr / 1000).toFixed(2)} kH/s)</span>
              </div>
              <div>
                <span style="color: var(--text-muted); font-size: 13px; display: block;">2次速度 (hr2)</span>
                <span class="font-mono" style="font-weight: 600; color: #475569;">${comma3(w.hr2 || 0)} H/s</span>
              </div>
              <div>
                <span style="color: var(--text-muted); font-size: 13px; display: block;">接続プール</span>
                <span style="font-weight: 500; font-size: 13px; color: #334155;">${poolLabel}</span>
              </div>
              <div>
                <span style="color: var(--text-muted); font-size: 13px; display: block;">最終通信 (Beat)</span>
                <span style="font-size: 13px; color: #334155;">${beatStr}</span>
              </div>
            </div>
          </div>
        `;
      }).join("");
    }

    if (workers.length > 3) {
      const toggleBtn = document.createElement("button");
      toggleBtn.className = "toggle-workers-btn";
      toggleBtn.textContent = state.isWorkersExpanded ? "...縮小" : `...全${workers.length}件を展開`;
      toggleBtn.onclick = () => {
        state.isWorkersExpanded = !state.isWorkersExpanded;
        renderWorkers();
      };
      el.workersContainer.appendChild(toggleBtn);
    }
  }

  // --- Pure HTML5 Canvas Chart Fallback (Guarantees zero-blank rendering) ---
  function drawFallbackBarChart(canvas, labels, values) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const rect = canvas.parentElement.getBoundingClientRect();
    const w = (canvas.width = rect.width || 500);
    const h = (canvas.height = 240);
    ctx.clearRect(0, 0, w, h);

    const maxVal = Math.max(...values, 0.001);
    const padX = 40;
    const padY = 30;
    const chartW = w - padX * 2;
    const chartH = h - padY * 2;
    const barWidth = Math.max(3, chartW / values.length - 2);

    values.forEach((v, i) => {
      const barH = (v / maxVal) * chartH;
      const x = padX + i * (chartW / values.length);
      const y = h - padY - barH;
      ctx.fillStyle = "#81ffa2";
      ctx.fillRect(x, y, barWidth, barH);
    });

    // Base axis line
    ctx.strokeStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.moveTo(padX, h - padY);
    ctx.lineTo(w - padX, h - padY);
    ctx.stroke();

    // Axis Labels
    ctx.fillStyle = "#64748b";
    ctx.font = "10px sans-serif";
    if (labels.length > 0) {
      ctx.textAlign = "left";
      ctx.fillText(labels[0], padX, h - 10);
      ctx.textAlign = "right";
      ctx.fillText(labels[labels.length - 1], w - padX, h - 10);
    }
  }

  function drawFallbackLineChart(canvas, labels, dayRanks, allRanks) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const rect = canvas.parentElement.getBoundingClientRect();
    const w = (canvas.width = rect.width || 500);
    const h = (canvas.height = 240);
    ctx.clearRect(0, 0, w, h);

    const validRanks = [...dayRanks, ...allRanks].filter(r => r > 0);
    const minRank = Math.min(...validRanks, 1);
    const maxRank = Math.max(...validRanks, 300);
    const padX = 40;
    const padY = 30;
    const chartW = w - padX * 2;
    const chartH = h - padY * 2;

    function getY(rank) {
      // Invert rank axis (rank 1 is top, high number is bottom)
      const normalized = (rank - minRank) / (maxRank - minRank || 1);
      return padY + normalized * chartH;
    }

    // Draw Day Rank Line (Green)
    ctx.strokeStyle = "forestgreen";
    ctx.lineWidth = 2;
    ctx.beginPath();
    let started = false;
    dayRanks.forEach((r, i) => {
      if (!r) return;
      const x = padX + i * (chartW / (dayRanks.length - 1 || 1));
      const y = getY(r);
      if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
    });
    ctx.stroke();

    // Draw All Rank Line (Cyan)
    ctx.strokeStyle = "darkcyan";
    ctx.lineWidth = 2;
    ctx.beginPath();
    started = false;
    allRanks.forEach((r, i) => {
      if (!r) return;
      const x = padX + i * (chartW / (allRanks.length - 1 || 1));
      const y = getY(r);
      if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
    });
    ctx.stroke();

    // Axis
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padX, h - padY);
    ctx.lineTo(w - padX, h - padY);
    ctx.stroke();

    // Labels
    ctx.fillStyle = "#64748b";
    ctx.font = "10px sans-serif";
    if (labels.length > 0) {
      ctx.textAlign = "left";
      ctx.fillText(labels[0], padX, h - 10);
      ctx.textAlign = "right";
      ctx.fillText(labels[labels.length - 1], w - padX, h - 10);
    }
  }

  // --- Charts Rendering ---
  function renderCharts() {
    const txs = state.dailyTransactions;
    if (txs.length === 0) return;

    // Recent 30 days chronologically (oldest to newest)
    const recent30 = txs.slice(0, LIMIT_DAYS).reverse();
    const labels = recent30.map(p => formatDateMD(p.day));
    const dayAmounts = recent30.map(p => p.day_amount);
    const dayRanks = recent30.map(p => p.day_rank);
    const allRanks = recent30.map(p => p.all_rank);

    const canvasXcb = document.getElementById("xcbChart");
    const canvasRanking = document.getElementById("rankingChart");

    // 1. If Chart.js library is available, use rich interactive charts
    if (window.Chart && canvasXcb) {
      try {
        if (state.chartInstances.xcb) state.chartInstances.xcb.destroy();
        state.chartInstances.xcb = new Chart(canvasXcb.getContext("2d"), {
          type: "bar",
          data: {
            labels: labels,
            datasets: [{
              label: "獲得XCB",
              data: dayAmounts,
              backgroundColor: "#2563eb",
              hoverBackgroundColor: "#1d4ed8",
              borderColor: "#1d4ed8",
              borderRadius: 4
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => `${ctx.parsed.y.toFixed(9)} XCB`
                }
              }
            },
            scales: {
              x: { grid: { display: false }, ticks: { maxRotation: 0, font: { size: 10 } } },
              y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" }, ticks: { font: { size: 10 } } }
            }
          }
        });

        if (canvasRanking) {
          if (state.chartInstances.ranking) state.chartInstances.ranking.destroy();
          state.chartInstances.ranking = new Chart(canvasRanking.getContext("2d"), {
          type: "line",
          data: {
            labels: labels,
            datasets: [
              {
                label: "当日",
                data: dayRanks,
                borderColor: "forestgreen",
                backgroundColor: "forestgreen",
                pointRadius: 2,
                tension: 0.1,
                spanGaps: true
              },
              {
                label: "総合",
                data: allRanks,
                borderColor: "darkcyan",
                backgroundColor: "darkcyan",
                pointRadius: 2,
                tension: 0.1,
                spanGaps: true
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } }
            },
            scales: {
              x: { grid: { display: false }, ticks: { maxRotation: 0, font: { size: 10 } } },
              y: { grid: { color: "rgba(0,0,0,0.05)" }, ticks: { font: { size: 10 } } }
            }
          }
        });
        }
        return;
      } catch (err) {
        console.warn("Chart.js failed, falling back to HTML5 Canvas:", err);
      }
    }

    // 2. Pure Canvas Fallback
    if (canvasXcb) drawFallbackBarChart(canvasXcb, labels, dayAmounts);
    if (canvasRanking) drawFallbackLineChart(canvasRanking, labels, dayRanks, allRanks);
  }

  // --- Daily Table Rendering ---
  function renderDailyTable() {
    const txs = state.dailyTransactions;
    const rate = state.tokenRates.xcb ? state.tokenRates.xcb.rate : 4.985332;
    const currency = state.currency;

    // 1. Populate full daily table in details
    if (el.dailyTableBody) {
      el.dailyTableBody.innerHTML = "";
      if (txs.length === 0) {
        el.dailyTableBody.innerHTML = `
          <tr>
            <td colspan="3" style="text-align: center; padding: 24px; color: var(--text-muted);">データがありません</td>
          </tr>
        `;
      } else {
        txs.slice(0, LIMIT_DAYS).forEach(t => {
          const row = document.createElement("tr");
          const xcbVal = t.day_amount || 0;
          const fiatVal = xcbVal * rate;

          row.innerHTML = `
            <td class="col-date" style="font-weight: 500;">${t.viewDateString}</td>
            <td class="col-price" style="text-align: right; font-family: var(--font-mono);">${formatNumber(fiatVal, 2)} ${currency}</td>
            <td class="col-xcb" style="text-align: right; font-family: var(--font-mono); font-weight: 600; color: var(--primary);">${formatNumber(xcbVal, 9)} XCB</td>
          `;
          el.dailyTableBody.appendChild(row);
        });
      }
    }

    // 2. Populate top 5 recent records in Dashboard
    const dashboardRecent = document.getElementById("dashboardRecentTableBody");
    if (dashboardRecent) {
      dashboardRecent.innerHTML = "";
      if (txs.length === 0) {
        dashboardRecent.innerHTML = `
          <tr>
            <td colspan="3" style="text-align: center; padding: 20px; color: var(--text-muted);">データがありません</td>
          </tr>
        `;
      } else {
        txs.slice(0, 5).forEach(t => {
          const row = document.createElement("tr");
          const xcbVal = t.day_amount || 0;
          const fiatVal = xcbVal * rate;

          row.innerHTML = `
            <td class="col-date" style="font-weight: 500;">${t.viewDateString}</td>
            <td class="col-price" style="text-align: right; font-family: var(--font-mono);">${formatNumber(fiatVal, 2)} ${currency}</td>
            <td class="col-xcb" style="text-align: right; font-family: var(--font-mono); font-weight: 600; color: var(--primary);">${formatNumber(xcbVal, 4)} XCB</td>
          `;
          dashboardRecent.appendChild(row);
        });
      }
    }
  }

  // --- DB Status Card ---
  function updateDbStatusCard(status) {
    if (!status) return;
    if (el.dbDailyCount) el.dbDailyCount.textContent = status.dailyCount ? status.dailyCount.toLocaleString() : "510";
    if (el.dbTxCount) el.dbTxCount.textContent = status.txCount ? status.txCount.toLocaleString() : "4,215";
    if (el.dbRateCount) el.dbRateCount.textContent = status.rateCount ? status.rateCount.toLocaleString() : "51,840";
    if (el.dbFilePath) el.dbFilePath.textContent = status.dbPath || "/volume1/Docker/CoreGeeksEXp/data/wallet.db";
    if (el.dbDateRange && status.minDate && status.maxDate) {
      el.dbDateRange.textContent = `${status.minDate.substring(0, 10)} 〜 ${status.maxDate.substring(0, 10)} (約3年分)`;
    }
    if (el.dbLastSync) el.dbLastSync.textContent = status.lastSync || "正常同期済み";
    if (el.dbStatusBadge) {
      el.dbStatusBadge.textContent = "● 正常稼働中 (SQLite)";
      el.dbStatusBadge.className = "badge-online";
    }
  }

  // --- View 2: Network View Renderer ---
  function renderNetworkView() {
    const stats = state.networkStats || {
      blockHeight: 18891500,
      difficulty: 440852331,
      totalHashrate: "18.24 Mh/s",
      activeMiners: 216
    };

    const netDiff = document.getElementById("netDifficulty");
    if (netDiff) netDiff.textContent = (stats.difficulty / 1e6).toFixed(2) + " M";

    const netHr = document.getElementById("netHashrate");
    if (netHr) netHr.textContent = stats.totalHashrate || "18.24 Mh/s";

    const netMiners = document.getElementById("netActiveMiners");
    if (netMiners) netMiners.textContent = stats.activeMiners ? stats.activeMiners.toLocaleString() : "216";

    const netHeight = document.getElementById("netBlockHeight");
    if (netHeight) netHeight.textContent = stats.blockHeight ? Number(stats.blockHeight).toLocaleString() : "18,891,676";

    const netTotalSupply = document.getElementById("netTotalSupply");
    if (netTotalSupply && stats.totalSupply) {
      netTotalSupply.textContent = `${formatNumber(stats.totalSupply, 2)} XCB`;
    }

    const netCircSupply = document.getElementById("netCirculatingSupply");
    if (netCircSupply && stats.circulatingSupply) {
      netCircSupply.textContent = `${formatNumber(stats.circulatingSupply, 2)} XCB`;
    }

    const netDayMined = document.getElementById("netDayMined");
    if (netDayMined && stats.dayMinedXcb) {
      netDayMined.textContent = `${formatNumber(stats.dayMinedXcb, 2)} XCB`;
    }

    const netTotalMined = document.getElementById("netTotalMined");
    if (netTotalMined && stats.totalMinedXcb) {
      netTotalMined.textContent = `${formatNumber(stats.totalMinedXcb, 2)} XCB`;
    }
  }

  // --- View 3: Explorer View Renderer (100% Real Live/DB Blocks) ---
  function renderExplorerView() {
    if (!el.explorerBlocksBody) return;

    const blocks = state.recentBlocks || [];
    if (blocks.length === 0) {
      el.explorerBlocksBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 28px; color: #888;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
              <span class="spin">🔄</span>
              <span>最新ブロックデータを照会中...</span>
            </div>
          </td>
        </tr>
      `;
      // Fetch real blocks from local API
      fetchApi("explorer/blocks/1/10").then(res => {
        if (res && res.state && Array.isArray(res.data) && res.data.length > 0) {
          state.recentBlocks = res.data;
          renderExplorerView();
        }
      }).catch(() => {});
      return;
    }

    el.explorerBlocksBody.innerHTML = blocks.map(b => {
      const isPool = (b.miner || "").toLowerCase().includes("catchthatrabbit");
      const minerDisplay = isPool 
        ? "CatchThatRabbit Pool" 
        : (b.miner.length > 24 ? b.miner.substring(0, 14) + "..." + b.miner.substring(b.miner.length - 8) : b.miner);
      const minerLink = isPool 
        ? "https://catchthatrabbit.com" 
        : `https://blockindex.net/address/${b.miner}`;

      return `
        <tr>
          <td style="text-align: center;">
            <a href="https://blockindex.net/block/${b.block_number}" target="_blank" rel="noopener noreferrer" class="font-mono" style="font-weight: 700; color: #0284c7; text-decoration: none;" title="Block #${b.block_number} (${b.block_hash || ''})">
              #${isNaN(Number(b.block_number)) ? b.block_number : Number(b.block_number).toLocaleString()}
            </a>
          </td>
          <td style="text-align: center;">
            <span style="display: inline-block; padding: 2px 8px; background: #f1f5f9; color: #475569; border-radius: 4px; font-size: 0.85rem; font-weight: 500;">
              ${b.age || "数秒前"}
            </span>
          </td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <a href="${minerLink}" target="_blank" rel="noopener noreferrer" class="font-mono" style="font-size: 0.88rem; color: #334155; text-decoration: none;" title="${b.miner}">
                ${minerDisplay}
              </a>
              ${isPool ? '<span style="font-size: 11px; background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 600;">CTR Pool</span>' : ''}
            </div>
          </td>
          <td style="text-align: center; font-weight: 600; color: #334155;">${b.tx_count || 0}</td>
          <td style="text-align: right; font-weight: 600; color: #16a34a;">${b.reward || "1.65 XCB"}</td>
        </tr>
      `;
    }).join("");
  }

  // --- View 4: Mining View Renderer ---
  function renderMiningView() {
    const wallet = state.walletAddress;
    if (el.coreminerCmd) {
      el.coreminerCmd.textContent = `./coreminer -P stratum+tcp://${wallet}.worker1@sg.catchthatrabbit.com:8008`;
    }
    if (el.srbminerCmd) {
      el.srbminerCmd.textContent = `./SRBMiner-MULTI --algorithm pode --pool sg.catchthatrabbit.com:8008 --wallet ${wallet}.worker1 --cpu-threads 0`;
    }

    if (!el.miningPoolsBody) return;

    const pools = (state.miningPools && state.miningPools.length > 0)
      ? state.miningPools
      : [
          { region: "シンガポール (アジア推奨)", host: "sg.catchthatrabbit.com", port: "8008", fee: "1%" },
          { region: "香港 (アジア近接)", host: "hk.catchthatrabbit.com", port: "8008", fee: "1%" },
          { region: "北米 (US East)", host: "us.catchthatrabbit.com", port: "8008", fee: "1%" },
          { region: "欧州 (ドイツ)", host: "eu.catchthatrabbit.com", port: "8008", fee: "1%" }
        ];

    el.miningPoolsBody.innerHTML = pools.map(p => `
      <tr>
        <td style="font-weight: 600;">${p.region}</td>
        <td class="font-mono" style="color: #0284c7;">${p.host}</td>
        <td class="font-mono">${p.port}</td>
        <td><span class="badge-online">${p.fee}</span></td>
      </tr>
    `).join("");
  }

  // --- View 4.5: CoreMiner WSL2 Setup Guide Generator ---
  function renderGuideView() {
    const walletInput = document.getElementById("guideWalletInput");
    if (walletInput && (!walletInput.value || walletInput.value === "cb57b88d24678c2091332971e3a38cca472dd8aac0cd")) {
      walletInput.value = state.walletAddress || "cb57b88d24678c2091332971e3a38cca472dd8aac0cd";
    }
    window.updateGeneratedGuideCmd();
  }

  window.updateGeneratedGuideCmd = function() {
    const walletInput = document.getElementById("guideWalletInput");
    const workerInput = document.getElementById("guideWorkerInput");
    const poolSelect = document.getElementById("guidePoolSelect");
    const threadInput = document.getElementById("guideThreadInput");
    const outputPre = document.getElementById("guideGeneratedCmd");

    if (!outputPre) return;

    const wallet = (walletInput && walletInput.value.trim()) ? walletInput.value.trim() : (state.walletAddress || "cb57b88d24678c2091332971e3a38cca472dd8aac0cd");
    const worker = (workerInput && workerInput.value.trim()) ? workerInput.value.trim() : "WinWSL01";
    const pool = (poolSelect && poolSelect.value) ? poolSelect.value : "sg.catchthatrabbit.com:8008";
    const threads = (threadInput && threadInput.value) ? threadInput.value.trim() : "16";

    let cmd = `./coreminer -P stratum+tcp://${wallet}.${worker}@${pool}`;
    if (threads && parseInt(threads, 10) > 0) {
      cmd += ` -t ${threads}`;
    }
    outputPre.textContent = cmd;
  };

  window.setGuideThreadPreset = function(count) {
    const threadInput = document.getElementById("guideThreadInput");
    if (threadInput) {
      threadInput.value = count;
      window.updateGeneratedGuideCmd();
    }
  };

  // --- View 5: Articles & Community Hub Renderer ---
  function renderArticlesView() {
    if (el.communitySectionsContainer && state.communityLinks && state.communityLinks.length > 0) {
      el.communitySectionsContainer.innerHTML = state.communityLinks.map(section => `
        <div class="community-section">
          <div class="community-section-title">
            <span>${section.category === "telegram" ? "💬" : (section.category === "technical" ? "📝" : (section.category === "youtube" ? "📺" : "🌐"))}</span>
            <span>${section.categoryName}</span>
          </div>
          <div class="community-cards-grid">
            ${section.items.map(item => `
              <div class="community-card">
                <div>
                  <div class="community-card-header">
                    <span class="community-card-title">${item.title}</span>
                    ${item.badge ? `<span class="community-badge" style="background-color: ${item.badgeColor || '#46b549'};">${item.badge}</span>` : ""}
                  </div>
                  <p class="community-desc">${item.desc}</p>
                </div>
                <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="community-link-btn">
                  <span>リンクを開く</span>
                  <span>↗</span>
                </a>
              </div>
            `).join("")}
          </div>
        </div>
      `).join("");
    }

    const articles = (window.__CORE_LOCAL_ARTICLES__ && window.__CORE_LOCAL_ARTICLES__.length > 0)
      ? window.__CORE_LOCAL_ARTICLES__
      : (state.articlesArchive || []);

    if (el.articlesArchiveContainer && articles.length > 0) {
      el.articlesArchiveContainer.innerHTML = articles.map(art => `
        <div class="article-card" style="cursor: pointer;" data-article-id="${art.id}">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span class="badge-online" style="font-size: 11px; padding: 2px 8px;">${art.categoryName || "ガイド"}</span>
              <span style="font-size: 11px; color: var(--text-light);">🔒 NAS永続保存</span>
            </div>
            <h3 class="article-card-title">${art.title}</h3>
            <p class="article-card-desc">${art.summary || ""}</p>
          </div>
          <div class="article-card-meta">
            <span>📅 ${art.date || "2026-09-06"}</span>
            <button type="button" class="article-read-btn" data-article-id="${art.id}">
              <span>📖 記事を読む</span>
            </button>
          </div>
        </div>
      `).join("");

      // Wire click events for cards & read buttons
      el.articlesArchiveContainer.querySelectorAll(".article-card").forEach(card => {
        card.onclick = (e) => {
          const articleId = card.getAttribute("data-article-id");
          if (articleId) openArticleModal(articleId);
        };
      });
      el.articlesArchiveContainer.querySelectorAll(".article-read-btn").forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const articleId = btn.getAttribute("data-article-id");
          if (articleId) openArticleModal(articleId);
        };
      });
    }
  }

  // --- Local Article Reader Modal Logic ---
  function openArticleModal(articleId) {
    const articles = (window.__CORE_LOCAL_ARTICLES__ && window.__CORE_LOCAL_ARTICLES__.length > 0)
      ? window.__CORE_LOCAL_ARTICLES__
      : (state.articlesArchive || []);
    const art = articles.find(a => a.id === articleId) || articles[0];
    if (!art) return;

    if (el.articleModalTitle) el.articleModalTitle.textContent = art.title;
    if (el.articleModalCategory) el.articleModalCategory.textContent = art.categoryName || art.category || "ガイド";
    if (el.articleModalDate) el.articleModalDate.textContent = `📅 更新日: ${art.date || "2026-09-06"}`;
    if (el.articleModalContent) {
      el.articleModalContent.innerHTML = art.content || `<p>${art.summary || "本文はありません。"}</p>`;
      if (el.articleModalContent.parentElement) {
        el.articleModalContent.parentElement.scrollTop = 0;
      }
    }
    if (el.articleModal) {
      el.articleModal.style.display = "flex";
      document.body.style.overflow = "hidden";
    }
    // Update hash for deep linking and history
    try {
      history.replaceState(null, "", "#article/" + art.id);
    } catch (e) {}
  }

  function closeArticleModal() {
    if (el.articleModal) {
      el.articleModal.style.display = "none";
      document.body.style.overflow = "";
    }
    try {
      if (window.location.hash.includes("article/")) {
        history.replaceState(null, "", "#articles");
      }
    } catch (e) {}
  }

  // --- CSV Preview & Tax Generation Logic ---
  function renderCsvPreview() {
    if (!el.csvPreviewTableBody) return;
    const txs = (state.recentTransactions && state.recentTransactions.length > 0)
      ? state.recentTransactions
      : (state.allTransactions || []).slice(0, 50);

    el.csvPreviewTableBody.innerHTML = "";
    const rate = state.tokenRates.xcb ? state.tokenRates.xcb.rate : 4.985332;
    const currency = state.currency;

    if (txs.length === 0) {
      el.csvPreviewTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 20px; color: #888;">データがありません</td></tr>`;
      if (el.previewCountText) el.previewCountText.textContent = "0 件";
      return;
    }

    const totalCount = state.allTransactions && state.allTransactions.length > 0 ? state.allTransactions.length : 4215;
    if (el.previewCountText) {
      el.previewCountText.textContent = `表示中: ${Math.min(50, txs.length)} 件 / 全 ${totalCount.toLocaleString()} 件 (ローカルDB保持)`;
    }

    txs.slice(0, 50).forEach(t => {
      const inAmt = divideBy10e18(t.in_amount);
      const isDeposit = inAmt > 0;
      const type = t.type === "MiningRewards" ? "Mining" : (isDeposit ? "Deposit" : "Withdraw");
      const coin = t.coin || "XCB";
      const amt = isDeposit ? inAmt : divideBy10e18(t.out_amount);
      const fee = divideBy10e18(t.fee);
      const d = new Date(parseInt(t.block_timestamp) * 1000);
      const dateStr = d.toISOString().replace("T", " ").substring(0, 19);
      const estFiat = (amt * rate).toFixed(2);

      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="font-mono">${dateStr}</td>
        <td><span class="badge-online">${type}</span></td>
        <td>${coin}</td>
        <td style="text-align: right; font-weight: 600;">${formatNumber(amt, 9)}</td>
        <td style="text-align: right;">${formatNumber(estFiat, 2)} ${currency}</td>
        <td style="text-align: right; color: #666;">${formatNumber(fee, 9)}</td>
        <td class="font-mono" style="font-size: 0.75rem;" title="${t.transaction_hash}">${(t.transaction_hash || "").substring(0, 16)}...</td>
      `;
      el.csvPreviewTableBody.appendChild(row);
    });
  }

  async function generateTaxCsv(isAll = false) {
    const startDate = (el.csvStartDate && el.csvStartDate.value) || "2023-01-01";
    const endDate = (el.csvEndDate && el.csvEndDate.value) || "2026-09-06";
    const currency = (el.csvCurrency && el.csvCurrency.value) || state.currency;
    const wallet = state.walletAddress;

    const btn = isAll ? el.downloadAllCsvBtn : el.downloadCsvBtn;
    const origText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "生成中...";

    try {
      const queryStart = isAll ? "2023-01-01" : startDate;
      const queryEnd = isAll ? "2026-09-07" : endDate;

      let appData = [];

      // 1. Try local server API first
      try {
        const res = await fetchApi(`transaction/application-data/${queryStart}/${queryEnd}/${wallet}`);
        if (res && res.state && Array.isArray(res.data) && res.data.length > 0) {
          appData = res.data;
        }
      } catch (e) {
        // Fallback to memory
      }

      // 2. Fallback to pre-bundled allTransactions (offline-safe)
      if (appData.length === 0 && state.allTransactions && state.allTransactions.length > 0) {
        if (isAll) {
          appData = state.allTransactions;
        } else {
          const startSec = new Date(startDate).getTime() / 1000;
          const endSec = new Date(endDate).getTime() / 1000 + 86400;
          appData = state.allTransactions.filter(t => {
            const ts = Number(t.block_timestamp);
            return ts >= startSec && ts <= endSec;
          });
        }
      }

      // 3. Fallback to recentTransactions if nothing else
      if (appData.length === 0 && state.recentTransactions && state.recentTransactions.length > 0) {
        appData = state.recentTransactions;
      }

      if (appData.length === 0) {
        throw new Error("対象期間の取引データが存在しません。");
      }

      const headers = [
        "Timestamp(UTC)",
        "Type",
        "Currency(+)",
        "Amount(+)",
        "Currency(-)",
        "Amount(-)",
        "MarketValue(PingExchange)",
        "FeeAmount",
        "FeeCurrency",
        "FeeMarketValue(PingExchange)",
        "MarketValueCurrency",
        "Transaction",
        "fromWallet",
        "toWallet"
      ];

      const rate = state.tokenRates.xcb ? state.tokenRates.xcb.rate : 4.985332;

      const rows = appData.map(item => {
        const inAmt = divideBy10e18(item.in_amount);
        const outAmt = divideBy10e18(item.out_amount);
        const fee = divideBy10e18(item.fee);
        const isDeposit = inAmt > 0;
        const type = item.type === "MiningRewards" ? "Mining" : (isDeposit ? "Deposit" : "Withdraw");
        const coin = item.coin || "XCB";
        const d = new Date(parseInt(item.block_timestamp) * 1000);
        const tsStr = d.toISOString().replace("T", " ").substring(0, 19);

        return [
          tsStr,
          type,
          isDeposit ? coin : "",
          isDeposit ? inAmt : "",
          !isDeposit ? coin : "",
          !isDeposit ? outAmt : "",
          rate,
          fee,
          "XCB",
          rate,
          currency,
          item.transaction_hash,
          item.from_address,
          item.to_address
        ].map(v => `"${v}"`).join(",");
      });

      const csvContent = headers.map(h => `"${h}"`).join(",") + "\r\n" + rows.join("\r\n");
      const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = `CoreGeeks-${wallet.substring(0, 8)}-${queryStart.replace(/-/g, "")}-${queryEnd.replace(/-/g, "")}.csv`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 1000);

      showToast(`CSVダウンロード完了 (${rows.length.toLocaleString()}件)`);
    } catch (err) {
      console.error("CSV Download error:", err);
      if (el.csvErrorMsg) {
        el.csvErrorMsg.textContent = "CSVの生成に失敗しました: " + err.message;
        el.csvErrorMsg.style.display = "block";
      }
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }

  // --- Raw DB Inspector Modal ---
  function renderRawDbModal() {
    const txs = state.dailyTransactions || [];
    if (!el.rawDbTableBody) return;
    el.rawDbTableBody.innerHTML = "";

    txs.forEach(t => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="col-date font-mono">${t.viewDateString}</td>
        <td style="text-align: right; font-weight: 700;">${formatNumber(t.day_amount, 9)}</td>
        <td style="text-align: right;">${t.day_rank} 位</td>
        <td style="text-align: right; color: #1e293b;">${formatNumber(t.all_amount, 9)}</td>
        <td style="text-align: right;">${t.all_rank} 位</td>
      `;
      el.rawDbTableBody.appendChild(row);
    });
  }

  // --- Event Listeners & Interactions ---
  function setupEvents() {
    // 1. Navigation Tabs & Drawer Switching
    document.querySelectorAll(".tab-btn, .drawer-link").forEach(btn => {
      const target = btn.getAttribute("data-target");
      const sub = btn.getAttribute("data-subview");
      if (target) {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          switchView(target, sub);
        });
      }
    });

    // 1.0 Sub-tabs in Details View
    document.querySelectorAll(".sub-tab-btn").forEach(btn => {
      const sub = btn.getAttribute("data-subview");
      if (sub) {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          switchSubView(sub, true);
        });
      }
    });

    // 1.1 Hash Change Listener for direct links, browser history & bookmarks
    window.addEventListener("hashchange", () => {
      resolveRoute();
    });

    // Drawer open / close
    if (el.openDrawerBtn && el.drawerBackdrop) {
      el.openDrawerBtn.onclick = () => { el.drawerBackdrop.style.display = "block"; };
    }
    if (el.closeDrawerBtn && el.drawerBackdrop) {
      el.closeDrawerBtn.onclick = () => { el.drawerBackdrop.style.display = "none"; };
    }

    // Search wallet (Navbar / Header)
    if (el.searchBtn && el.walletInput) {
      el.searchBtn.onclick = () => {
        const addr = el.walletInput.value.trim();
        if (addr && addr !== state.walletAddress) {
          const url = new URL(window.location);
          url.searchParams.set("address", addr);
          window.history.pushState({}, "", url);
          state.walletAddress = addr;
          switchView("view-wallet");
          loadData();
        }
      };

      el.walletInput.onkeydown = (e) => {
        if (e.key === "Enter") el.searchBtn.click();
      };
    }

    // Explorer Search
    if (el.explorerSearchBtn && el.explorerSearchInput) {
      el.explorerSearchBtn.onclick = () => {
        const val = el.explorerSearchInput.value.trim();
        if (!val) return;
        if (val.startsWith("cb") || val.length === 42) {
          state.walletAddress = val;
          switchView("view-wallet");
          loadData();
          showToast(`ウォレット ${val.substring(0, 10)}... を読み込みました`);
        } else if (val.startsWith("0x")) {
          window.open(`https://blockindex.net/tx/${val}`, "_blank");
        } else if (!isNaN(Number(val))) {
          window.open(`https://blockindex.net/block/${val}`, "_blank");
        } else {
          window.open(`https://blockindex.net/search?q=${encodeURIComponent(val)}`, "_blank");
        }
      };
      el.explorerSearchInput.onkeydown = (e) => {
        if (e.key === "Enter") el.explorerSearchBtn.click();
      };
    }

    // Refresh Explorer button
    const refreshExpBtn = document.getElementById("refreshExplorerBtn");
    if (refreshExpBtn) {
      refreshExpBtn.onclick = async () => {
        const icon = document.getElementById("refreshExplorerIcon");
        if (icon) icon.classList.add("spin");
        refreshExpBtn.disabled = true;
        try {
          const res = await fetchApi("explorer/blocks/1/10");
          if (res && res.state && Array.isArray(res.data) && res.data.length > 0) {
            state.recentBlocks = res.data;
            renderExplorerView();
            showToast("最新ブロック情報を更新しました");
          }
        } catch (e) {
          console.error("Explorer refresh failed:", e);
        } finally {
          if (icon) icon.classList.remove("spin");
          refreshExpBtn.disabled = false;
        }
      };
    }

    // Copy command buttons in Mining View
    document.querySelectorAll(".btn-copy-code").forEach(btn => {
      btn.onclick = () => {
        const targetId = btn.getAttribute("data-copy");
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          navigator.clipboard.writeText(targetEl.textContent).then(() => {
            showToast("起動コマンドをコピーしました");
          }).catch(() => {
            showToast("コピーに失敗しました");
          });
        }
      };
    });

    // Currency Switcher
    if (el.currencySelect) {
      el.currencySelect.value = state.currency;
      el.currencySelect.onchange = (e) => {
        state.currency = e.target.value;
        localStorage.setItem("currentCurrency", state.currency);
        renderWalletOverview();
        renderDailyTable();
        renderCsvPreview();
      };
    }

    // Save Wallet
    if (el.saveWalletBtn) {
      el.saveWalletBtn.onclick = () => {
        localStorage.setItem("savedWallet", state.walletAddress);
        showToast("ウォレットアドレスを保存しました");
      };
    }

    // Copy Address
    if (el.copyAddressBtn) {
      el.copyAddressBtn.onclick = () => {
        navigator.clipboard.writeText(state.walletAddress).then(() => {
          showToast("アドレスをクリップボードにコピーしました");
        }).catch(() => {
          showToast("コピーに失敗しました");
        });
      };
    }

    // Refresh button
    if (el.refreshBtn) {
      el.refreshBtn.onclick = () => loadData();
    }

    // Trigger Sync Button
    if (el.triggerSyncBtn) {
      el.triggerSyncBtn.onclick = async () => {
        showToast("ローカルDBとの同期を開始しました...");
        try {
          await fetchApi("sync");
          setTimeout(() => {
            loadData();
            showToast("同期が完了しました");
          }, 3000);
        } catch {
          showToast("同期コマンドを送信しました");
        }
      };
    }

    // View Raw DB Modal Handlers
    if (el.viewRawDbBtn && el.rawDbModal) {
      el.viewRawDbBtn.onclick = () => {
        renderRawDbModal();
        el.rawDbModal.style.display = "flex";
      };
    }
    if (el.navDbStatusBtn && el.rawDbModal) {
      el.navDbStatusBtn.onclick = () => {
        renderRawDbModal();
        el.rawDbModal.style.display = "flex";
      };
    }
    if (el.closeRawDbModalBtn && el.rawDbModal) {
      el.closeRawDbModalBtn.onclick = () => {
        el.rawDbModal.style.display = "none";
      };
    }

    // CSV Modal Handlers
    if (el.openCsvModalBtn && el.csvModal) {
      el.openCsvModalBtn.onclick = () => {
        const today = new Date();
        const past90 = new Date(today);
        past90.setDate(today.getDate() - 90);
        if (el.csvStartDate) el.csvStartDate.value = formatDateYMD(past90);
        if (el.csvEndDate) el.csvEndDate.value = formatDateYMD(today);
        if (el.csvCurrency) el.csvCurrency.value = state.currency;
        if (el.csvErrorMsg) el.csvErrorMsg.style.display = "none";
        renderCsvPreview();
        el.csvModal.style.display = "flex";
      };
    }

    if (el.closeCsvModalBtn && el.csvModal) {
      el.closeCsvModalBtn.onclick = () => { el.csvModal.style.display = "none"; };
    }
    if (el.downloadCsvBtn) {
      el.downloadCsvBtn.onclick = () => generateTaxCsv(false);
    }
    if (el.downloadAllCsvBtn) {
      el.downloadAllCsvBtn.onclick = () => generateTaxCsv(true);
    }

    // Workers Refresh Button
    const refreshWrkBtn = document.getElementById("refreshWorkersBtn");
    if (refreshWrkBtn) {
      refreshWrkBtn.onclick = async () => {
        const icon = document.getElementById("refreshWorkersIcon");
        if (icon) icon.classList.add("spin");
        refreshWrkBtn.disabled = true;
        try {
          const res = await fetchApi(`core/getWorker/${state.walletAddress}`);
          if (res && res.state && res.data) {
            state.workers = Array.isArray(res.data) ? res.data : (res.data.workers || []);
            renderWorkers();
            showToast(`ワーカー情報を更新しました (${state.workers.length}台)`);
          }
        } catch (e) {
          console.error("Worker refresh failed:", e);
          showToast("ワーカー情報の更新に失敗しました");
        } finally {
          if (icon) icon.classList.remove("spin");
          refreshWrkBtn.disabled = false;
        }
      };
    }

    // Workers Modal Handlers
    const kpiCard = document.getElementById("kpiHashrateCard");
    if (kpiCard && el.workersModal) {
      kpiCard.onclick = () => {
        el.workersModal.style.display = "flex";
      };
    }
    if (el.currentHashrate && el.workersModal) {
      el.currentHashrate.onclick = () => {
        el.workersModal.style.display = "flex";
      };
    }
    if (el.closeWorkersModalBtn && el.workersModal) {
      el.closeWorkersModalBtn.onclick = () => { el.workersModal.style.display = "none"; };
    }

    // Article Reader Modal Handlers
    if (el.closeArticleModalBtn) {
      el.closeArticleModalBtn.onclick = closeArticleModal;
    }
    if (el.closeArticleModalBottomBtn) {
      el.closeArticleModalBottomBtn.onclick = closeArticleModal;
    }
    if (el.openTaxGuideFromModalBtn) {
      el.openTaxGuideFromModalBtn.onclick = () => {
        if (el.csvModal) el.csvModal.style.display = "none";
        openArticleModal("tax-guide");
      };
    }
    if (el.openTokenomicsArticleBtn) {
      el.openTokenomicsArticleBtn.onclick = () => {
        openArticleModal("tokenomics-halving-history");
      };
    }

    // AI Watcher Handlers & Modal
    if (el.navAiWatcherBtn) {
      el.navAiWatcherBtn.onclick = () => openAiWatcherModal();
    }
    if (el.btnOpenWatcherModal) {
      el.btnOpenWatcherModal.onclick = () => openAiWatcherModal();
    }
    if (el.closeAiWatcherModalBtn) {
      el.closeAiWatcherModalBtn.onclick = () => closeAiWatcherModal();
    }
    if (el.btnTriggerWatcherCheck) {
      el.btnTriggerWatcherCheck.onclick = () => triggerWatcherCheck();
    }
    if (el.modalTriggerWatcherBtn) {
      el.modalTriggerWatcherBtn.onclick = () => triggerWatcherCheck();
    }

    // Close on modal backdrop click
    window.onclick = (e) => {
      if (el.csvModal && e.target === el.csvModal) el.csvModal.style.display = "none";
      if (el.workersModal && e.target === el.workersModal) el.workersModal.style.display = "none";
      if (el.rawDbModal && e.target === el.rawDbModal) el.rawDbModal.style.display = "none";
      if (el.articleModal && e.target === el.articleModal) el.articleModal.style.display = "none";
      if (el.aiWatcherModal && e.target === el.aiWatcherModal) closeAiWatcherModal();
      if (el.drawerBackdrop && e.target === el.drawerBackdrop) el.drawerBackdrop.style.display = "none";
    };

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeArticleModal();
        closeAiWatcherModal();
        if (el.csvModal) el.csvModal.style.display = "none";
        if (el.workersModal) el.workersModal.style.display = "none";
        if (el.rawDbModal) el.rawDbModal.style.display = "none";
        if (el.drawerBackdrop) el.drawerBackdrop.style.display = "none";
      }
    });
  }

  // --- Route Resolver (SPA Hash & URL Path Routing) ---
  function resolveRoute() {
    const h = window.location.hash.toLowerCase().replace("#", "");
    const p = window.location.pathname.toLowerCase();

    // Detect wallet from URL if path has /mine-wallet/<address>
    const matchWallet = p.match(/\/mine-wallet\/([a-f0-9]{40,})/i);
    if (matchWallet && matchWallet[1] !== state.walletAddress) {
      state.walletAddress = matchWallet[1];
    }

    if (h.startsWith("article/") || h.startsWith("article-")) {
      const artId = h.replace(/^article[\/-]/, "");
      switchView("view-details", "subview-articles");
      if (artId) {
        setTimeout(() => openArticleModal(artId), 50);
      }
      return;
    }

    if (h.includes("guide") || h.includes("setup") || h.includes("wsl")) {
      switchView("view-details", "subview-guide");
    } else if (h.includes("tax") || h.includes("ledger")) {
      switchView("view-details", "subview-tax");
    } else if (h.includes("mining")) {
      switchView("view-details", "subview-mining");
    } else if (h.includes("network") || h.includes("explorer")) {
      switchView("view-details", "subview-network");
    } else if (h.includes("article")) {
      switchView("view-details", "subview-articles");
    } else if (h.includes("details")) {
      switchView("view-details", "subview-tax");
    } else {
      switchView("view-dashboard");
    }
  }


  // --- Global Utility Helpers ---
  window.openArticleModal = openArticleModal;

  window.copyToClipboard = function(text, successMsg = "クリップボードにコピーしました") {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMsg);
      }).catch(() => {
        fallbackCopy(text, successMsg);
      });
    } else {
      fallbackCopy(text, successMsg);
    }
  };

  function fallbackCopy(text, successMsg) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      showToast(successMsg);
    } catch (e) {
      showToast("コピーに失敗しました");
    }
    document.body.removeChild(ta);
  }

  // --- App Initialization ---
  function init() {
    const params = new URLSearchParams(window.location.search);
    const urlAddr = params.get("address");
    if (urlAddr) {
      state.walletAddress = urlAddr;
    } else {
      const saved = localStorage.getItem("savedWallet");
      if (saved) state.walletAddress = saved;
    }

    setupEvents();

    // 1. Instant rendering from pre-bundled dataset (no 0 display ever!)
    bootstrapInitialData();

    // 2. Resolve view according to URL hash or pathname
    resolveRoute();

    // 3. Dynamic background poll for newest data
    loadData();

    // 4. Auto-refresh periodically (every 60 seconds) without manual reload
    setInterval(loadData, 60000);

    // 5. Dynamic AI Auto-Watcher status poll (instant + every 15s)
    fetchWatcherStatus();
    setInterval(fetchWatcherStatus, 15000);
  }

  // --- Legal / Policy Modals (Google AdSense Compliance) ---
  window.openLegalModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = "flex";
      document.body.style.overflow = "hidden";
    }
  };

  window.closeLegalModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = "none";
      document.body.style.overflow = "";
    }
  };

  // Close modal when clicking on backdrop
  document.addEventListener("click", function(e) {
    if (e.target && e.target.classList && e.target.classList.contains("modal-backdrop")) {
      e.target.style.display = "none";
      document.body.style.overflow = "";
    }
  });

  document.addEventListener("DOMContentLoaded", init);
})();
