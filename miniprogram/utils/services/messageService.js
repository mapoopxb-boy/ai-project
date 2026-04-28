/**
 * 消息发送服务模块
 * 负责处理 AI 对话请求和响应
 * 
 * 创建时间：2026-04-29
 * 版本：v1.0
 */

const { aiChat } = require('../request.js');
const storage = require('../modules/storage.js');

// ============== 配置常量 ==============
const DEFAULT_AGENT = "auto";
const LOADING_TIP = "AI正在思考中...";

// ============== 消息服务类 ==============
class MessageService {
  constructor() {
    this.currentAgent = DEFAULT_AGENT;
  }

  /**
   * 设置当前使用的 Agent
   * @param {string} agentType - Agent 类型
   */
  setAgent(agentType) {
    this.currentAgent = agentType || DEFAULT_AGENT;
    console.log(`[MessageService] Agent 已设置: ${this.currentAgent}`);
  }

  /**
   * 获取当前 Agent
   * @returns {string}
   */
  getAgent() {
    return this.currentAgent;
  }

  /**
   * 发送消息并获取 AI 回复
   * @param {string} content - 用户输入内容
   * @param {string} userId - 用户ID
   * @returns {Promise<Object>} - AI 响应
   */
  async sendMessage(content, userId) {
    if (!content || !content.trim()) {
      throw new Error('消息内容不能为空');
    }

    console.log(`[MessageService] 发送消息: ${content.substring(0, 50)}...`);
    console.log(`[MessageService] 当前Agent: ${this.currentAgent}`);
    console.log(`[MessageService] 用户ID: ${userId}`);

    try {
      // 调用 API
      const response = await aiChat(content, userId, this.currentAgent);
      
      console.log(`[MessageService] 收到响应, Agent: ${response.agent}`);
      
      // 格式化响应
      return this.formatResponse(response);
      
    } catch (error) {
      console.error('[MessageService] 发送失败:', error);
      throw error;
    }
  }

  /**
   * 格式化 API 响应
   * @param {Object} response - API 原始响应
   * @returns {Object} - 格式化后的响应
   */
  formatResponse(response) {
    // 图片生成
    if (response.image_url) {
      return {
        type: 'image',
        content: response.image_url,
        text: response.answer,
        agent: response.agent
      };
    }
    
    // 新闻数据
    if (response.news_data && response.news_data.length > 0) {
      let newsText = response.answer;
      return {
        type: 'news',
        content: newsText,
        newsData: response.news_data,
        agent: response.agent
      };
    }
    
    // 普通文本
    return {
      type: 'text',
      content: response.answer || '暂时无法回复',
      agent: response.agent
    };
  }

  /**
   * 生成消息对象
   * @param {string} role - 角色: 'user' 或 'ai'
   * @param {string} type - 消息类型: 'text', 'image', 'file', 'video'
   * @param {string} content - 消息内容
   * @param {Object} extra - 额外参数
   * @returns {Object} - 消息对象
   */
  createMessage(role, type, content, extra = {}) {
    const message = {
      id: this.generateId(),
      role: role,
      type: type,
      content: content,
      time: new Date().toLocaleTimeString(),
      ...extra
    };
    
    return message;
  }

  /**
   * 生成唯一ID
   * @returns {string}
   */
  generateId() {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// 导出单例
const messageService = new MessageService();
module.exports = messageService;
