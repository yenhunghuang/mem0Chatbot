/**
 * 投資顧問助理 - 主應用程式
 * 
 * 整合儲存層、API 客戶端和 UI，實作完整的聊天邏輯。
 */

// DOM 元素
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const messageForm = document.getElementById('messageForm');
const messagesContainer = document.getElementById('messages');
const statusDiv = document.getElementById('status');
const loadingDiv = document.getElementById('loading');
const errorToast = document.getElementById('errorToast');
const newChatBtn = document.getElementById('newChatBtn');
const memoriesDiv = document.getElementById('memories');
const sidebarDiv = document.getElementById('sidebar');

// 記憶管理 DOM 元素 (T062)
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const memoriesListDiv = document.getElementById('memoriesList');
const memorySearchInput = document.getElementById('memorySearchInput');
const refreshMemoriesBtn = document.getElementById('refreshMemoriesBtn');
const deleteAllMemoriesBtn = document.getElementById('deleteAllMemoriesBtn');

// 應用狀態
let appState = {
  userId: null,
  conversationId: null,
  isLoading: false,
};

/**
 * 初始化應用程式
 */
function initApp() {
  console.log('[App] 初始化應用程式');
  
  // 初始化儲存層
  initStorage();
  
  // 取得或建立使用者 ID
  appState.userId = getUserId();
  console.log(`[App] 使用者 ID: ${appState.userId}`);
  
  // 取得現有對話 ID
  appState.conversationId = getConversationId();
  
  // 綁定事件
  messageForm.addEventListener('submit', handleSendMessage);
  newChatBtn.addEventListener('click', handleNewChat);
  messageInput.addEventListener('keydown', handleKeyDown);
  
  // 綁定記憶管理事件 (T062)
  bindMemoryEvents();
  
  // 檢查 API 健康狀態
  checkApiHealth();
  
  console.log('[App] 應用程式已初始化');
}

/**
 * 檢查 API 健康狀態
 */
async function checkApiHealth() {
  const isHealthy = await checkHealth();
  
  if (!isHealthy) {
    showError('無法連接到伺服器，請檢查網路連接');
    disableInput();
  }
}

/**
 * 處理發送訊息
 */
async function handleSendMessage(event) {
  event.preventDefault();
  
  const message = messageInput.value.trim();
  
  if (!message) {
    showError('請輸入訊息');
    return;
  }
  
  if (appState.isLoading) {
    return;
  }
  
  // 清除輸入框
  messageInput.value = '';
  messageInput.style.height = '50px';
  
  // 顯示使用者訊息
  addMessageToUI('user', message);
  
  // 禁用輸入
  setLoading(true);
  
  try {
    // 發送訊息
    const response = await sendMessage(
      appState.userId,
      appState.conversationId,
      message
    );
    
    if (!response || response.code !== 'SUCCESS') {
      throw new Error(response?.message || '伺服器回應異常');
    }
    
    // 更新對話 ID
    const newConversationId = response.data?.conversation_id;
    if (newConversationId && !appState.conversationId) {
      appState.conversationId = newConversationId;
      setConversationId(newConversationId);
      console.log(`[App] 建立新對話: ${newConversationId}`);
    }
    
    // 顯示助理回應
    const assistantMessage = response.data?.assistant_message?.content;
    if (assistantMessage) {
      addMessageToUI('assistant', assistantMessage);
    }
    
    // 顯示使用的記憶
    const memoriesUsed = response.data?.memories_used || [];
    updateMemoriesDisplay(memoriesUsed);
    
    // 清除狀態
    clearStatus();
    
  } catch (error) {
    console.error('[App] 發送訊息失敗:', error);
    const errorMsg = getErrorMessage(error);
    showError(errorMsg);
    
    // 在 UI 中顯示錯誤訊息
    addMessageToUI('system', `❌ ${errorMsg}`);
  } finally {
    setLoading(false);
  }
}

/**
 * 處理新對話
 */
function handleNewChat() {
  if (confirm('確定要開始新對話嗎？')) {
    clearConversationId();
    appState.conversationId = null;
    messagesContainer.innerHTML = '';
    memoriesDiv.innerHTML = '<p class="empty">目前沒有使用的記憶</p>';
    clearStatus();
    
    // 重新添加歡迎訊息
    addMessageToUI('system', '歡迎使用投資顧問助理！您可以詢問任何投資相關問題，我會根據您的偏好提供個人化建議。');
    addMessageToUI('system', '💡 提示：告訴我您的投資偏好、風險承受度或具體的投資問題，系統將自動記住您的信息。');
    
    console.log('[App] 已開始新對話');
  }
}

/**
 * 處理鍵盤事件
 */
function handleKeyDown(event) {
  if (event.ctrlKey && event.key === 'Enter') {
    messageForm.dispatchEvent(new Event('submit'));
  }
}

/**
 * 新增訊息到 UI
 * 
 * @param {string} role - 角色 (user/assistant/system)
 * @param {string} content - 訊息內容
 */
function addMessageToUI(role, content) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  
  const pElement = document.createElement('p');
  pElement.textContent = content;
  
  messageDiv.appendChild(pElement);
  messagesContainer.appendChild(messageDiv);
  
  // 自動捲動到最新訊息
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * 更新記憶顯示（US2 T043 - 支援字典格式記憶）
 * 
 * @param {Array<string|Object>} memories - 使用的記憶列表（字串或字典格式）
 */
function updateMemoriesDisplay(memories) {
  if (!memories || memories.length === 0) {
    memoriesDiv.innerHTML = '<p class="empty">目前沒有使用的記憶</p>';
    sidebarDiv.classList.remove('active');
    return;
  }
  
  sidebarDiv.classList.add('active');
  
  memoriesDiv.innerHTML = memories
    .map((memory, index) => {
      // 📌 從統一格式提取數據
      let content = '';
      let relevance = 0;
      
      if (typeof memory === 'object' && memory !== null) {
        // 提取內容（Mem0 標準格式使用 'content' 欄位）
        content = memory.content || memory.memory || '';
        
        // 📌 只從頂層讀取 relevance_score（單一數據源）
        relevance = memory.relevance_score || 0;
        
        console.log(`[App] 記憶 ${index + 1}: "${content.substring(0, 30)}...", 相關度=${relevance}`);
      } else {
        // 備用：字串格式
        content = String(memory);
        relevance = 0;
        console.log(`[App] 記憶 ${index + 1}: 字串格式 "${content.substring(0, 30)}..."`);
      }
      
      // 建立記憶項目
      let memoryHTML = `<div class="memory-item">`;
      
      // 計算百分比和顏色等級
      const percent = Math.round(relevance * 100);
      let relevanceClass = 'low';
      
      if (percent >= 80) {
        relevanceClass = 'high';
      } else if (percent >= 50) {
        relevanceClass = 'medium';
      }
      
      // 顯示相關度徽章
      memoryHTML += `<span class="relevance-badge ${relevanceClass}">${percent}%</span>`;
      memoryHTML += `<span class="memory-content">${escapeHtml(content)}</span></div>`;
      
      return memoryHTML;
    })
    .join('');
  
  console.log(`[App] 顯示 ${memories.length} 條使用的記憶`);
}

/**
 * 設定載入狀態
 * 
 * @param {boolean} isLoading - 是否載入中
 */
function setLoading(isLoading) {
  appState.isLoading = isLoading;
  sendBtn.disabled = isLoading;
  messageInput.disabled = isLoading;
  
  if (isLoading) {
    loadingDiv.classList.add('active');
    statusDiv.textContent = '正在處理您的請求...';
    statusDiv.className = 'status loading';
  } else {
    loadingDiv.classList.remove('active');
  }
}

/**
 * 顯示錯誤訊息
 * 
 * @param {string} message - 錯誤訊息
 */
function showError(message) {
  errorToast.textContent = message;
  errorToast.classList.add('active');
  
  // 3 秒後自動隱藏
  setTimeout(() => {
    errorToast.classList.remove('active');
  }, 3000);
  
  statusDiv.textContent = `錯誤: ${message}`;
  statusDiv.className = 'status error';
}

/**
 * 清除狀態訊息
 */
function clearStatus() {
  statusDiv.textContent = '';
  statusDiv.className = 'status';
}

/**
 * 禁用輸入
 */
function disableInput() {
  messageInput.disabled = true;
  sendBtn.disabled = true;
}

/**
 * 啟用輸入
 */
function enableInput() {
  messageInput.disabled = false;
  sendBtn.disabled = false;
}

/**
 * 顯示載入指示器
 */
function showLoading() {
  loadingDiv.classList.add('active');
}

/**
 * 隱藏載入指示器
 */
function hideLoading() {
  loadingDiv.classList.remove('active');
}

/**
 * 從錯誤物件取得錯誤訊息
 * 
 * @param {Error} error - 錯誤物件
 * @returns {string} 錯誤訊息
 */
function getErrorMessage(error) {
  if (typeof error === 'string') {
    return error;
  }
  
  if (error.message) {
    return error.message;
  }
  
  return '發生未知錯誤';
}

/**
 * HTML 轉義
 * 
 * @param {string} text - 要轉義的文字
 * @returns {string} 轉義後的文字
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * 記憶管理事件綁定 (T062)
 */
function bindMemoryEvents() {
  // 標籤頁切換
  tabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const tabName = btn.dataset.tab;
      switchTab(tabName);
    });
  });
  
  // 記憶列表刷新
  if (refreshMemoriesBtn) {
    refreshMemoriesBtn.addEventListener('click', loadMemories);
  }
  
  // 清除所有記憶
  if (deleteAllMemoriesBtn) {
    deleteAllMemoriesBtn.addEventListener('click', handleDeleteAllMemories);
  }
  
  // 搜索記憶
  if (memorySearchInput) {
    memorySearchInput.addEventListener('input', debounce(handleMemorySearch, 300));
  }
}

/**
 * 切換標籤頁
 */
function switchTab(tabName) {
  // 更新按鈕狀態
  tabBtns.forEach(btn => {
    if (btn.dataset.tab === tabName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  
  // 更新內容顯示
  tabContents.forEach(content => {
    if (content.dataset.tab === tabName) {
      content.classList.add('active');
      // 切換到記憶標籤時載入記憶
      if (tabName === 'memories') {
        loadMemories();
      }
    } else {
      content.classList.remove('active');
    }
  });
  
  console.log(`[Memory] 切換到標籤: ${tabName}`);
}

/**
 * 載入並顯示記憶列表
 */
async function loadMemories() {
  if (!appState.userId) {
    console.error('[Memory] 使用者 ID 未設置');
    return;
  }
  
  showLoading();
  
  try {
    const response = await listMemories(appState.userId, { limit: 100 });
    displayMemories(response.data || []);
  } catch (error) {
    console.error('[Memory] 載入記憶失敗:', error);
    showError('無法載入記憶: ' + getErrorMessage(error));
  } finally {
    hideLoading();
  }
}

/**
 * 顯示記憶列表
 */
function displayMemories(memories) {
  if (!memories || memories.length === 0) {
    memoriesListDiv.innerHTML = `
      <div class="empty-state">
        <p>還沒有保存的記憶</p>
        <p class="hint">在對話中分享您的投資偏好，系統會自動保存</p>
      </div>
    `;
    return;
  }
  
  memoriesListDiv.innerHTML = memories.map(memory => `
    <div class="memory-card" data-memory-id="${escapeHtml(memory.id)}">
      <div class="memory-card-header">
        <div>
          ${memory.category ? `<span class="memory-badge">${escapeHtml(memory.category)}</span>` : ''}
        </div>
        <div class="memory-actions">
          <button class="btn-memory btn-edit" onclick="editMemory('${escapeHtml(memory.id)}', '${escapeHtml(memory.content)}')">
            ✏️ 編輯
          </button>
          <button class="btn-memory btn-danger" onclick="deleteMemoryItem('${escapeHtml(memory.id)}')">
            🗑️ 刪除
          </button>
        </div>
      </div>
      <div class="memory-content">
        ${escapeHtml(memory.content)}
      </div>
      <div class="memory-meta">
        <span>ID: ${escapeHtml(memory.id.substring(0, 8))}...</span>
        ${memory.timestamp ? `<span>時間: ${escapeHtml(memory.timestamp.substring(0, 10))}</span>` : ''}
        ${memory.relevance_score ? `<span>相關度: ${(memory.relevance_score * 100).toFixed(0)}%</span>` : ''}
      </div>
    </div>
  `).join('');
  
  console.log(`[Memory] 已顯示 ${memories.length} 個記憶`);
}

/**
 * 刪除單一記憶
 */
async function deleteMemoryItem(memoryId) {
  if (!confirm('確定要刪除此記憶嗎？')) {
    return;
  }
  
  showLoading();
  
  try {
    await deleteMemory(memoryId);
    showNotification('記憶已刪除');
    await loadMemories();
  } catch (error) {
    console.error('[Memory] 刪除失敗:', error);
    showError('無法刪除記憶: ' + getErrorMessage(error));
  } finally {
    hideLoading();
  }
}

/**
 * 編輯記憶
 */
function editMemory(memoryId, content) {
  const newContent = prompt('編輯記憶內容:', content);
  
  if (newContent === null) {
    return; // 使用者取消
  }
  
  if (newContent.trim() === '') {
    showError('記憶內容不能為空');
    return;
  }
  
  updateMemoryItem(memoryId, newContent);
}

/**
 * 更新記憶
 */
async function updateMemoryItem(memoryId, content) {
  showLoading();
  
  try {
    await updateMemory(memoryId, { content: content });
    showNotification('記憶已更新');
    await loadMemories();
  } catch (error) {
    console.error('[Memory] 更新失敗:', error);
    showError('無法更新記憶: ' + getErrorMessage(error));
  } finally {
    hideLoading();
  }
}

/**
 * 刪除所有記憶
 */
async function handleDeleteAllMemories() {
  if (!confirm('確定要刪除所有記憶嗎？此操作無法撤銷！')) {
    return;
  }
  
  showLoading();
  
  try {
    const result = await batchDeleteMemories(appState.userId);
    showNotification(`已刪除 ${result.deleted_count} 個記憶`);
    await loadMemories();
  } catch (error) {
    console.error('[Memory] 批量刪除失敗:', error);
    showError('無法刪除記憶: ' + getErrorMessage(error));
  } finally {
    hideLoading();
  }
}

/**
 * 搜索記憶
 */
async function handleMemorySearch(e) {
  const query = e.target.value.trim();
  
  if (!query) {
    // 搜索框為空，載入所有記憶
    await loadMemories();
    return;
  }
  
  if (!appState.userId) {
    return;
  }
  
  showLoading();
  
  try {
    const response = await searchMemories(appState.userId, query, { top_k: 20 });
    displayMemories(response.results || []);
  } catch (error) {
    console.error('[Memory] 搜索失敗:', error);
    showError('搜索失敗: ' + getErrorMessage(error));
  } finally {
    hideLoading();
  }
}

/**
 * 防抖函數
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * 顯示通知
 */
function showNotification(message) {
  const toast = document.createElement('div');
  toast.className = 'success-toast active';
  toast.style.cssText = `
    position: fixed;
    bottom: var(--spacing-lg, 24px);
    right: var(--spacing-lg, 24px);
    background-color: #10b981;
    color: white;
    padding: var(--spacing-md, 16px) var(--spacing-lg, 24px);
    border-radius: var(--border-radius, 8px);
    box-shadow: var(--shadow-lg, 0 10px 15px -3px rgb(0 0 0 / 0.1));
    z-index: 999;
    animation: slideInRight 0.3s ease-in-out;
  `;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

/**
 * 初始化應用程式 (修改後)
 */
window.addEventListener('DOMContentLoaded', initApp);

/**
 * 自動調整文字區域高度
 */
messageInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

// 頁面載入時初始化
document.addEventListener('DOMContentLoaded', initApp);

// 頁面卸載時清理
window.addEventListener('beforeunload', function() {
  console.log('[App] 應用程式正在卸載');
});

console.log('[App] app.js 已載入');
