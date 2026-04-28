// utils/request.js
const baseUrl = "http://127.0.0.1:8000";

const request = (url, method = "GET", data = {}) => {
  return new Promise((resolve, reject) => {
    let token = wx.getStorageSync("token") || "";
    console.log("当前token：", token);
    console.log("请求地址：", baseUrl + url);
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

module.exports = {
  // aiChat 函数：agentType 默认值为 "auto"，实现自动路由
  aiChat: (prompt, userId, agentType = "auto") => {
    if (!userId) userId = "test_user";
    console.log("发送请求 - agentType:", agentType);
    console.log("发送请求 - prompt:", prompt);
    return request("/ai-assistant", "POST", {
      user_input: prompt,
      user_id: userId,
      agent_type: agentType
    });
  }
};