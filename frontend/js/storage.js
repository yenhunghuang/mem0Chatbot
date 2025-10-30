/**
 * 儲存層 - 本地儲存管理
 * 
 * 負責管理使用者 ID 和對話 ID 的本地儲存。
 */

/**
 * 使用者 ID 儲存鑰匙
 */
const USER_ID_KEY = 'investment_advisor_user_id';

/**
 * 對話 ID 儲存鑰匙
 */
const CONVERSATION_ID_KEY = 'investment_advisor_conversation_id';

/**
 * 取得或建立使用者 ID
 * 
 * 如果本地儲存中已有 user_id，則返回該 ID。
 * 否則生成新 UUID 並儲存。
 * 
 * @returns {string} 使用者 ID (UUID v4 格式)
 */
function getUserId() {
  let userId = localStorage.getItem(USER_ID_KEY);
  
  if (!userId) {
    // 生成新 UUID v4
    userId = generateUUID();
    localStorage.setItem(USER_ID_KEY, userId);
    console.log(`[Storage] 生成新使用者 ID: ${userId}`);
  } else {
    console.log(`[Storage] 取得現有使用者 ID: ${userId}`);
  }
  
  return userId;
}

/**
 * 取得對話 ID
 * 
 * @returns {number|null} 對話 ID，如果未設定則返回 null
 */
function getConversationId() {
  const conversationId = localStorage.getItem(CONVERSATION_ID_KEY);
  
  if (conversationId) {
    return parseInt(conversationId, 10);
  }
  
  return null;
}

/**
 * 設定對話 ID
 * 
 * @param {number} conversationId - 對話 ID
 */
function setConversationId(conversationId) {
  localStorage.setItem(CONVERSATION_ID_KEY, conversationId.toString());
  console.log(`[Storage] 設定對話 ID: ${conversationId}`);
}

/**
 * 清除對話 ID
 * 
 * 清除本地儲存的對話 ID，開始新對話時呼叫。
 */
function clearConversationId() {
  localStorage.removeItem(CONVERSATION_ID_KEY);
  console.log(`[Storage] 清除對話 ID`);
}

/**
 * 重設使用者 ID
 * 
 * 生成新的使用者 ID 並清除舊的對話 ID。
 * 
 * @returns {string} 新的使用者 ID
 */
function resetUserId() {
  const newUserId = generateUUID();
  localStorage.setItem(USER_ID_KEY, newUserId);
  clearConversationId();
  console.log(`[Storage] 重設使用者 ID: ${newUserId}`);
  return newUserId;
}

/**
 * 生成 UUID v4
 * 
 * 使用 crypto.randomUUID() 生成符合 RFC 4122 的隨機 UUID。
 * 如果瀏覽器不支援，則使用備用實作。
 * 
 * @returns {string} UUID v4 字串
 */
function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  
  // 備用實作 (RFC 4122 v4)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * 驗證 UUID 格式
 * 
 * @param {string} uuid - 要驗證的 UUID 字串
 * @returns {boolean} 是否有效的 UUID
 */
function isValidUUID(uuid) {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

/**
 * 初始化儲存層
 * 
 * 確保 user_id 已初始化。
 */
function initStorage() {
  getUserId(); // 確保 user_id 存在
  console.log('[Storage] 儲存層已初始化');
}

// 匯出模組
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getUserId,
    getConversationId,
    setConversationId,
    clearConversationId,
    resetUserId,
    generateUUID,
    isValidUUID,
    initStorage,
    USER_ID_KEY,
    CONVERSATION_ID_KEY,
  };
}
