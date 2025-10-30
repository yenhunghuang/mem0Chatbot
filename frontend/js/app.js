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
    .map((memory) => {
      // 支援字典格式和字串格式
      let content = memory;
      let relevance = null;
      
      if (typeof memory === 'object' && memory !== null) {
        content = memory.content || memory.text || '';
        relevance = memory.metadata?.relevance;
      }
      
      // 建立記憶項目
      let memoryHTML = `<div class="memory-item">`;
      
      // 顯示相關度徽章（如果有）
      if (relevance !== null && typeof relevance === 'number') {
        const percent = Math.round(relevance * 100);
        const relevanceClass = percent >= 80 ? 'high' : percent >= 50 ? 'medium' : 'low';
        memoryHTML += `<span class="relevance-badge ${relevanceClass}">${percent}%</span>`;
      }
      
      memoryHTML += `<span class="memory-content">${escapeHtml(content)}</span></div>`;
      
      return memoryHTML;
    })
    .join('');
  
  // 在控制台顯示記憶信息（用於調試）
  console.log('[App] 使用的記憶:', memories);
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
