// utils/request.js
const baseUrl = "http://127.0.0.1:8000";

/**
 * 发起 HTTP 请求
 * @param {string} url - 请求路径
 * @param {string} method - GET/POST/PUT/DELETE
 * @param {object} data - 请求体数据
 * @returns {Promise<any>}
 */
const request = (url, method = "GET", data = {}) => {
  return new Promise((resolve, reject) => {
    let token = wx.getStorageSync("token") || "";
    console.log("请求地址：", baseUrl + url);
    console.log("请求方法：", method);
    console.log("请求参数：", data);

    wx.request({
      url: baseUrl + url,
      method: method,
      data: data,
      header: {
        "Content-Type": "application/json",
        "token": token
      },
      success: (res) => {
        console.log("后端返回：", res.data);
        if (res.data.code === 401 || res.data.msg === "需要重新登录") {
          wx.showToast({ title: "请先登录", icon: "none" });
          wx.navigateTo({ url: "/pages/login/login" });
          reject("请登录");
          return;
        }
        resolve(res.data);
      },
      fail: (err) => {
        console.error("请求失败：", err);
        reject(err);
      }
    });
  });
};

// 封装通用 API 调用
const api = {
  get: (url, data = {}) => request(url, "GET", data),
  post: (url, data = {}) => request(url, "POST", data),
  put: (url, data = {}) => request(url, "PUT", data),
  del: (url, data = {}) => request(url, "DELETE", data),
};

module.exports = {
  // 原始 request 函数（保留兼容）
  request,
  // 通用 API 对象
  api,
  // aiChat 函数
  aiChat: (prompt, userId, agentType = "auto") => {
    if (!userId) userId = "test_user";
    return request("/ai-assistant", "POST", {
      user_input: prompt,
      user_id: userId,
      agent_type: agentType
    });
  }
};
