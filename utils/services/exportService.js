/**
 * 聊天记录导出服务模块
 * 负责保存、分享聊天记录
 * 
 * 创建时间：2026-04-29
 * 版本：v1.0
 */

// ============== 导出服务类 ==============
class ExportService {
  constructor() {
    this.defaultFileName = '聊天记录';
  }

  /**
   * 格式化选中的消息为文本
   * @param {Array} messages - 选中的消息列表
   * @param {string} title - 对话标题
   * @param {string} sessionTitle - 会话标题
   * @returns {string} - 格式化后的文本
   */
  formatMessages(messages, title, sessionTitle) {
    let content = `🤖 AI助手聊天记录\n`;
    content += `对话名称：${sessionTitle || '未命名'}\n`;
    content += `导出时间：${new Date().toLocaleString()}\n`;
    content += `导出标题：${title || this.defaultFileName}\n`;
    content += `${'='.repeat(40)}\n\n`;
    
    messages.forEach((msg, index) => {
      const role = msg.role === 'user' ? '👤 我' : '🤖 AI助手';
      const time = msg.time || '';
      let messageContent = msg.content || '';
      
      // 处理特殊消息类型
      if (msg.type === 'image') {
        messageContent = `[图片] ${messageContent}`;
      } else if (msg.type === 'video') {
        messageContent = `[视频] ${messageContent}`;
      } else if (msg.type === 'file') {
        messageContent = `[文件] ${msg.fileName || '文件'}`;
      }
      
      // 图片生成附带文字
      if (msg.text) {
        messageContent += `\n[生成说明] ${msg.text}`;
      }
      
      content += `\n${role}`;
      if (time) content += ` (${time})`;
      content += `：\n${messageContent}\n`;
      content += `${'-'.repeat(30)}\n`;
    });
    
    return content;
  }

  /**
   * 保存到本地缓存
   * @param {string} content - 文件内容
   * @param {string} fileName - 文件名
   * @returns {Promise<string>} - 保存的文件路径
   */
  saveToCache(content, fileName) {
    return new Promise((resolve, reject) => {
      const fs = wx.getFileSystemManager();
      const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;
      
      wx.showLoading({ title: '保存中...' });
      
      fs.writeFile({
        filePath: filePath,
        data: content,
        encoding: 'utf8',
        success: () => {
          wx.hideLoading();
          wx.showModal({
            title: '保存成功',
            content: `文件已保存到缓存目录\n文件名：${fileName}`,
            showCancel: false
          });
          resolve(filePath);
        },
        fail: (err) => {
          wx.hideLoading();
          wx.showToast({ title: '保存失败', icon: 'none' });
          reject(err);
        }
      });
    });
  }

  /**
   * 分享给朋友
   * @param {string} content - 文件内容
   * @param {string} fileName - 文件名
   * @returns {Promise<void>}
   */
  shareToFriend(content, fileName) {
    return new Promise((resolve, reject) => {
      const fs = wx.getFileSystemManager();
      const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;
      
      wx.showLoading({ title: '准备中...' });
      
      fs.writeFile({
        filePath: filePath,
        data: content,
        encoding: 'utf8',
        success: () => {
          wx.hideLoading();
          wx.shareFileMessage({
            filePath: filePath,
            fileName: fileName,
            success: () => {
              wx.showToast({ title: '分享成功', icon: 'success' });
              resolve();
            },
            fail: (err) => {
              wx.showToast({ title: '分享失败', icon: 'none' });
              reject(err);
            }
          });
        },
        fail: (err) => {
          wx.hideLoading();
          wx.showToast({ title: '准备失败', icon: 'none' });
          reject(err);
        }
      });
    });
  }

  /**
   * 复制到剪贴板
   * @param {string} content - 要复制的内容
   * @returns {Promise<void>}
   */
  copyToClipboard(content) {
    return new Promise((resolve, reject) => {
      wx.setClipboardData({
        data: content,
        success: () => {
          wx.showToast({ title: '已复制到剪贴板', icon: 'success' });
          resolve();
        },
        fail: (err) => {
          wx.showToast({ title: '复制失败', icon: 'none' });
          reject(err);
        }
      });
    });
  }

  /**
   * 生成默认文件名
   * @returns {string}
   */
  generateDefaultFileName() {
    const now = new Date();
    const year = now.getFullYear();
    const month = (now.getMonth() + 1).toString().padStart(2, '0');
    const day = now.getDate().toString().padStart(2, '0');
    const hour = now.getHours().toString().padStart(2, '0');
    const minute = now.getMinutes().toString().padStart(2, '0');
    return `聊天记录_${year}${month}${day}_${hour}${minute}`;
  }
}

// 导出单例
const exportService = new ExportService();
module.exports = exportService;
