/**
 * 文件上传服务模块
 * 负责处理图片、视频、文件的上传和分析
 * 
 * 创建时间：2026-04-29
 * 版本：v1.0
 */

const { aiChat } = require('../request.js');
const storage = require('../modules/storage.js');

// ============== 配置常量 ==============
const MAX_VIDEO_DURATION = 60;  // 视频最大时长（秒）
const DEFAULT_QUESTION = {
  image: '请分析这张图片的内容，描述你看到了什么。',
  video: '请分析这个视频的内容。',
  file: '请分析这个文件的内容，并总结要点。'
};

// ============== 上传服务类 ==============
class UploadService {
  constructor() {
    this.currentAgent = "auto";
  }

  /**
   * 设置当前 Agent
   * @param {string} agentType 
   */
  setAgent(agentType) {
    this.currentAgent = agentType || "auto";
  }

  // ========== 文件选择方法 ==========

  /**
   * 显示上传选项菜单
   * @param {Function} onSelect - 选择后的回调
   */
  showUploadOptions(onSelect) {
    wx.showActionSheet({
      itemList: ['拍照', '从相册选择图片', '选择视频', '从聊天记录选择文件'],
      success: (res) => {
        const actions = ['camera', 'album', 'video', 'file'];
        if (onSelect && actions[res.tapIndex]) {
          onSelect(actions[res.tapIndex]);
        }
      }
    });
  }

  /**
   * 拍照
   * @returns {Promise<Object>} - 图片信息
   */
  takePhoto() {
    return new Promise((resolve, reject) => {
      wx.chooseMedia({
        count: 1,
        mediaType: ['image'],
        sourceType: ['camera'],
        success: (res) => {
          const tempFile = res.tempFiles[0];
          resolve({
            path: tempFile.tempFilePath,
            type: 'image',
            size: tempFile.size
          });
        },
        fail: reject
      });
    });
  }

  /**
   * 从相册选择图片
   * @returns {Promise<Object>} - 图片信息
   */
  chooseImageFromAlbum() {
    return new Promise((resolve, reject) => {
      wx.chooseMedia({
        count: 1,
        mediaType: ['image'],
        sourceType: ['album'],
        success: (res) => {
          const tempFile = res.tempFiles[0];
          resolve({
            path: tempFile.tempFilePath,
            type: 'image',
            size: tempFile.size
          });
        },
        fail: reject
      });
    });
  }

  /**
   * 选择视频
   * @returns {Promise<Object>} - 视频信息
   */
  chooseVideo() {
    return new Promise((resolve, reject) => {
      wx.chooseVideo({
        sourceType: ['album', 'camera'],
        maxDuration: MAX_VIDEO_DURATION,
        success: (res) => {
          resolve({
            path: res.tempFilePath,
            type: 'video',
            duration: res.duration,
            size: res.size
          });
        },
        fail: reject
      });
    });
  }

  /**
   * 从聊天记录选择文件
   * @returns {Promise<Object>} - 文件信息
   */
  chooseFileFromChat() {
    return new Promise((resolve, reject) => {
      wx.chooseMessageFile({
        count: 1,
        type: 'file',
        success: (res) => {
          const file = res.tempFiles[0];
          resolve({
            path: file.path,
            type: 'file',
            name: file.name,
            size: file.size
          });
        },
        fail: reject
      });
    });
  }

  // ========== 文件分析方法 ==========

  /**
   * 分析上传的文件
   * @param {Object} fileInfo - 文件信息
   * @param {string} userQuestion - 用户问题（可选）
   * @returns {Promise<Object>} - 分析结果
   */
  async analyzeFile(fileInfo, userQuestion = '') {
    const { path, type, name, size } = fileInfo;
    
    // 确定问题文本
    let question = userQuestion;
    if (!question) {
      switch (type) {
        case 'image':
          question = DEFAULT_QUESTION.image;
          break;
        case 'video':
          question = DEFAULT_QUESTION.video;
          break;
        default:
          question = DEFAULT_QUESTION.file;
      }
    }
    
    // 如果是文件类型，在问题中包含文件名
    if (type === 'file' && name) {
      question = `请分析文件"${name}"的内容，并总结要点。`;
    }
    
    console.log(`[UploadService] 分析文件: ${type}, 路径: ${path}`);
    
    try {
      const userId = storage.getUserId();
      const response = await aiChat(question, userId, this.currentAgent);
      
      return {
        success: true,
        answer: response.answer || '分析完成',
        agent: response.agent
      };
    } catch (error) {
      console.error('[UploadService] 分析失败:', error);
      return {
        success: false,
        answer: '分析失败，请稍后重试',
        error: error.message
      };
    }
  }

  /**
   * 格式化文件大小
   * @param {number} bytes - 字节数
   * @returns {string} - 格式化后的大小
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * 创建用户消息对象
   * @param {Object} fileInfo - 文件信息
   * @returns {Object} - 消息对象
   */
  createUserMessage(fileInfo) {
    const { type, path, name, size } = fileInfo;
    
    const message = {
      id: this.generateId(),
      role: 'user',
      type: type,
      content: type === 'image' ? path : 
               (type === 'video' ? path : `已上传文件：${name || '文件'}`),
      time: new Date().toLocaleTimeString()
    };
    
    if (type === 'file') {
      message.fileName = name;
      message.fileSize = this.formatFileSize(size);
    }
    
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
const uploadService = new UploadService();
module.exports = uploadService;
