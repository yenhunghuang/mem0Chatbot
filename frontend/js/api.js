/**
 * API 客戶端
 * 
 * 提供與後端 API 的通訊介面。
 */

/**
 * API 基礎 URL
 */
const API_BASE_URL = '/api/v1';

/**
 * API 請求超時 (毫秒)
 */
const REQUEST_TIMEOUT = 30000;

/**
 * 發送聊天訊息
 * 
 * @param {string} userId - 使用者 ID
 * @param {number|null} conversationId - 對話 ID (可選)
 * @param {string} message - 訊息內容
 * @returns {Promise<Object>} 聊天回應
 * @throws {Error} 如果請求失敗
 */
async function sendMessage(userId, conversationId, message) {
  console.log(`[API] 發送訊息: user_id=${userId}, conversation_id=${conversationId}`);
  
  const payload = {
    user_id: userId,
    message: message,
  };
  
  if (conversationId) {
    payload.conversation_id = conversationId;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      timeout: REQUEST_TIMEOUT,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.message || response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[API] 聊天回應成功:`, data);
    
    return data;
    
  } catch (error) {
    console.error('[API] 發送訊息失敗:', error);
    throw error;
  }
}

/**
 * 建立新對話
 * 
 * @param {string} userId - 使用者 ID
 * @returns {Promise<Object>} 新建立的對話
 * @throws {Error} 如果請求失敗
 */
async function createConversation(userId) {
  console.log(`[API] 建立對話: user_id=${userId}`);
  
  const payload = {
    user_id: userId,
  };
  
  try {
    const response = await fetch(`${API_BASE_URL}/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      timeout: REQUEST_TIMEOUT,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.message || response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[API] 建立對話成功:`, data);
    
    return data;
    
  } catch (error) {
    console.error('[API] 建立對話失敗:', error);
    throw error;
  }
}

/**
 * 取得對話訊息
 * 
 * @param {number} conversationId - 對話 ID
 * @param {number} limit - 最大返回數量
 * @returns {Promise<Object>} 訊息列表
 * @throws {Error} 如果請求失敗
 */
async function getConversationMessages(conversationId, limit = 50) {
  console.log(`[API] 取得對話訊息: conversation_id=${conversationId}`);
  
  try {
    const url = new URL(`${API_BASE_URL}/conversations/${conversationId}/messages`, window.location.origin);
    url.searchParams.append('limit', limit);
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: REQUEST_TIMEOUT,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.message || response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[API] 取得訊息成功:`, data);
    
    return data;
    
  } catch (error) {
    console.error('[API] 取得訊息失敗:', error);
    throw error;
  }
}

/**
 * 檢查 API 健康狀態
 * 
 * @returns {Promise<boolean>} API 是否健康
 */
async function checkHealth() {
  console.log('[API] 檢查 API 健康狀態');
  
  try {
    const response = await fetch('/health', {
      method: 'GET',
      timeout: 5000,
    });
    
    const isHealthy = response.ok;
    console.log(`[API] 健康檢查結果: ${isHealthy ? '正常' : '異常'}`);
    
    return isHealthy;
    
  } catch (error) {
    console.error('[API] 健康檢查失敗:', error);
    return false;
  }
}

/**
 * 將 API 錯誤轉換為使用者友善訊息
 * 
 * @param {Error} error - 錯誤物件
 * @returns {string} 使用者友善的錯誤訊息
 */
function getErrorMessage(error) {
  if (!error) {
    return '發生未知錯誤';
  }
  
  const message = error.message || error.toString();
  
  if (message.includes('timeout')) {
    return '請求超時，請檢查網路連接';
  }
  
  if (message.includes('VALIDATION_ERROR')) {
    return '輸入驗證失敗，請檢查訊息內容';
  }
  
  if (message.includes('LLM_ERROR')) {
    return 'LLM 服務暫時不可用，請稍後再試';
  }
  
  if (message.includes('DATABASE_ERROR')) {
    return '資料庫操作失敗，請稍後再試';
  }
  
  if (message.includes('503')) {
    return '服務暫時不可用，請稍後再試';
  }
  
  if (message.includes('500')) {
    return '伺服器內部錯誤，請稍後再試';
  }
  
  return message;
}

// 匯出模組
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    sendMessage,
    createConversation,
    getConversationMessages,
    checkHealth,
    getErrorMessage,
    API_BASE_URL,
    REQUEST_TIMEOUT,
  };
}
