/**
 * 存储管理模块
 * 负责小程序所有本地存储的读写操作
 * 
 * 创建时间：2026-04-29
 * 版本：v1.0
 */

// ============== 存储键名常量 ==============
const STORAGE_KEYS = {
  // 对话相关
  SESSIONS: 'chat_sessions',           // 所有对话列表
  CURRENT_SESSION: 'current_session',  // 当前激活的对话ID
  
  // 用户相关
  USER_ID: 'user_id',                  // 用户ID
  TOKEN: 'token',                      // 登录token
  USER_INFO: 'userInfo',               // 用户信息
  
  // 历史记录
  INPUT_HISTORY: 'input_history_',     // 输入历史（需要拼接用户ID）
  
  // 设置相关
  SETTINGS: 'app_settings'             // 应用设置
};

// ============== 存储管理类 ==============
class StorageManager {
  constructor() {
    this.keys = STORAGE_KEYS;
  }

  // ========== 通用方法（底层）==========
  
  set(key, data) {
    try {
      wx.setStorageSync(key, data);
      console.log(`[Storage] ✅ 保存成功: ${key}`);
      return true;
    } catch (e) {
      console.error(`[Storage] ❌ 保存失败: ${key}`, e);
      return false;
    }
  }

  get(key, defaultValue = null) {
    try {
      const data = wx.getStorageSync(key);
      if (data !== '' && data !== undefined) {
        console.log(`[Storage] 📖 读取成功: ${key}`);
        return data;
      }
      return defaultValue;
    } catch (e) {
      console.error(`[Storage] ❌ 读取失败: ${key}`, e);
      return defaultValue;
    }
  }

  remove(key) {
    try {
      wx.removeStorageSync(key);
      console.log(`[Storage] 🗑️ 删除成功: ${key}`);
      return true;
    } catch (e) {
      console.error(`[Storage] ❌ 删除失败: ${key}`, e);
      return false;
    }
  }

  clear() {
    try {
      wx.clearStorageSync();
      console.log('[Storage] 🧹 清空所有数据成功');
      return true;
    } catch (e) {
      console.error('[Storage] ❌ 清空失败', e);
      return false;
    }
  }

  // ========== 对话管理相关 ==========
  
  saveSessions(sessions) {
    return this.set(this.keys.SESSIONS, sessions);
  }

  getSessions() {
    return this.get(this.keys.SESSIONS, []);
  }

  saveCurrentSessionId(sessionId) {
    return this.set(this.keys.CURRENT_SESSION, sessionId);
  }

  getCurrentSessionId() {
    return this.get(this.keys.CURRENT_SESSION, null);
  }

  saveSessionMessages(sessionId, messages) {
    const sessions = this.getSessions();
    const index = sessions.findIndex(s => s.id === sessionId);
    
    if (index !== -1) {
      sessions[index] = {
        ...sessions[index],
        messages: messages,
        updateTime: Date.now()
      };
    } else {
      sessions.push({
        id: sessionId,
        title: '新对话',
        messages: messages,
        createTime: Date.now(),
        updateTime: Date.now()
      });
    }
    
    return this.saveSessions(sessions);
  }

  getSessionMessages(sessionId) {
    const sessions = this.getSessions();
    const session = sessions.find(s => s.id === sessionId);
    return session ? session.messages : [];
  }

  createNewSession(title = '新对话') {
    const newSession = {
      id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      title: title,
      messages: [],
      createTime: Date.now(),
      updateTime: Date.now()
    };
    
    const sessions = this.getSessions();
    sessions.unshift(newSession);
    this.saveSessions(sessions);
    
    console.log(`[Storage] ✨ 创建新对话: ${newSession.id}`);
    return newSession;
  }

  deleteSession(sessionId) {
    const sessions = this.getSessions();
    const newSessions = sessions.filter(s => s.id !== sessionId);
    
    if (newSessions.length === sessions.length) {
      console.warn(`[Storage] 对话不存在: ${sessionId}`);
      return false;
    }
    
    this.saveSessions(newSessions);
    
    const currentId = this.getCurrentSessionId();
    if (currentId === sessionId) {
      this.remove(this.keys.CURRENT_SESSION);
    }
    
    console.log(`[Storage] 🗑️ 删除对话: ${sessionId}`);
    return true;
  }

  updateSessionTitle(sessionId, newTitle) {
    const sessions = this.getSessions();
    const index = sessions.findIndex(s => s.id === sessionId);
    
    if (index !== -1) {
      sessions[index].title = newTitle;
      sessions[index].updateTime = Date.now();
      this.saveSessions(sessions);
      return true;
    }
    return false;
  }

  // ========== 输入历史相关 ==========
  
  getInputHistory(userId) {
    const key = this.keys.INPUT_HISTORY + (userId || 'default');
    return this.get(key, []);
  }

  saveInputHistory(userId, history) {
    const key = this.keys.INPUT_HISTORY + (userId || 'default');
    return this.set(key, history);
  }

  addToInputHistory(userId, content) {
    if (!content || !content.trim()) {
      return this.getInputHistory(userId);
    }
    
    let history = this.getInputHistory(userId);
    history = history.filter(item => item !== content);
    history.unshift(content);
    if (history.length > 5) {
      history = history.slice(0, 5);
    }
    
    this.saveInputHistory(userId, history);
    return history;
  }

  // ========== 用户相关 ==========
  
  getUserId() {
    let userId = this.get(this.keys.USER_ID);
    if (!userId) {
      userId = `user_${Date.now()}`;
      this.set(this.keys.USER_ID, userId);
    }
    return userId;
  }

  saveUserInfo(userInfo) {
    return this.set(this.keys.USER_INFO, userInfo);
  }

  getUserInfo() {
    return this.get(this.keys.USER_INFO, null);
  }

  saveToken(token) {
    return this.set(this.keys.TOKEN, token);
  }

  getToken() {
    return this.get(this.keys.TOKEN, '');
  }

  // ========== 设置相关 ==========
  
  saveSettings(settings) {
    return this.set(this.keys.SETTINGS, settings);
  }

  getSettings() {
    return this.get(this.keys.SETTINGS, {});
  }

  getSetting(key, defaultValue) {
    const settings = this.getSettings();
    return settings[key] !== undefined ? settings[key] : defaultValue;
  }

  saveSetting(key, value) {
    const settings = this.getSettings();
    settings[key] = value;
    return this.saveSettings(settings);
  }
}

// ============== 导出模块 ==============
const storage = new StorageManager();

// 微信小程序需要使用 CommonJS 格式
module.exports = storage;
module.exports.STORAGE_KEYS = STORAGE_KEYS;
