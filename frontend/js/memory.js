/**
 * 記憶管理 API 客戶端 (T060)
 * 
 * 提供記憶 CRUD 操作的 API 介面。
 */

/**
 * 取得使用者的記憶列表
 * 
 * @param {string} userId - 使用者 ID
 * @param {Object} options - 選項
 * @param {number} options.limit - 返回數量限制 (預設: 100)
 * @param {string} options.category - 記憶類別過濾 (可選)
 * @returns {Promise<Object>} 記憶列表
 * @throws {Error} 如果請求失敗
 */
async function listMemories(userId, options = {}) {
  console.log(`[Memory API] 取得記憶列表: user_id=${userId}`, options);
  
  const { limit = 100, category } = options;
  
  try {
    const url = new URL(`${API_BASE_URL}/memories`, window.location.origin);
    url.searchParams.append('user_id', userId);
    url.searchParams.append('limit', limit);
    if (category) {
      url.searchParams.append('category', category);
    }
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: REQUEST_TIMEOUT,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.detail || response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[Memory API] 取得記憶成功 (${data.count}): `, data);
    
    return data;
    
  } catch (error) {
    console.error('[Memory API] 取得記憶失敗:', error);
    throw error;
  }
}

/**
 * 刪除單一記憶
 * 
 * @param {string} memoryId - 記憶 ID
 * @returns {Promise<void>}
 * @throws {Error} 如果請求失敗
 */
async function deleteMemory(memoryId) {
  console.log(`[Memory API] 刪除記憶: memory_id=${memoryId}`);
  
  try {
    const response = await fetch(`${API_BASE_URL}/memories/${memoryId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: REQUEST_TIMEOUT,
    });
    
    // 204 No Content 表示成功刪除
    if (response.status !== 204 && !response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.detail || response.statusText}`);
    }
    
    console.log(`[Memory API] 刪除記憶成功`);
    
  } catch (error) {
    console.error('[Memory API] 刪除記憶失敗:', error);
    throw error;
  }
}

/**
 * 更新記憶
 * 
 * @param {string} memoryId - 記憶 ID
 * @param {Object} updateData - 更新資料
 * @param {string} updateData.content - 新的記憶內容
 * @param {string} updateData.category - 記憶類別 (可選)
 * @returns {Promise<Object>} 更新後的記憶
 * @throws {Error} 如果請求失敗
 */
async function updateMemory(memoryId, updateData) {
  console.log(`[Memory API] 更新記憶: memory_id=${memoryId}`, updateData);
  
  try {
    const payload = {
      content: updateData.content,
    };
    
    if (updateData.category) {
      payload.category = updateData.category;
    }
    
    const response = await fetch(`${API_BASE_URL}/memories/${memoryId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      timeout: REQUEST_TIMEOUT,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.detail || response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[Memory API] 更新記憶成功:`, data);
    
    return data;
    
  } catch (error) {
    console.error('[Memory API] 更新記憶失敗:', error);
    throw error;
  }
}

/**
 * 批量刪除記憶
 * 
 * @param {string} userId - 使用者 ID
 * @param {Object} options - 選項
 * @param {string} options.category - 要刪除的記憶類別 (可選)
 * @returns {Promise<Object>} 刪除結果 { deleted_count, timestamp }
 * @throws {Error} 如果請求失敗
 */
async function batchDeleteMemories(userId, options = {}) {
  console.log(`[Memory API] 批量刪除記憶: user_id=${userId}`, options);
  
  const payload = {
    user_id: userId,
  };
  
  if (options.category) {
    payload.category = options.category;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/memories/batch-delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      timeout: REQUEST_TIMEOUT,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.detail || response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[Memory API] 批量刪除成功 (${data.deleted_count}): `, data);
    
    return data;
    
  } catch (error) {
    console.error('[Memory API] 批量刪除失敗:', error);
    throw error;
  }
}

/**
 * 語義搜索記憶
 * 
 * @param {string} userId - 使用者 ID
 * @param {string} query - 搜索查詢
 * @param {Object} options - 選項
 * @param {number} options.top_k - 返回結果數量 (預設: 5)
 * @returns {Promise<Object>} 搜索結果
 * @throws {Error} 如果請求失敗
 */
async function searchMemories(userId, query, options = {}) {
  console.log(`[Memory API] 搜索記憶: user_id=${userId}, query=${query}`, options);
  
  const { top_k = 5 } = options;
  
  const payload = {
    user_id: userId,
    query: query,
    top_k: top_k,
  };
  
  try {
    const response = await fetch(`${API_BASE_URL}/memories/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      timeout: REQUEST_TIMEOUT,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API 錯誤 (${response.status}): ${errorData.detail || response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[Memory API] 搜索成功 (${data.results?.length || 0}): `, data);
    
    return data;
    
  } catch (error) {
    console.error('[Memory API] 搜索失敗:', error);
    throw error;
  }
}

// 匯出模組
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    listMemories,
    deleteMemory,
    updateMemory,
    batchDeleteMemories,
    searchMemories,
  };
}
