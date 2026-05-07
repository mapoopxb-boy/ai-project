// pages/rehab/index.js
const { aiChat } = require('../../utils/request.js');

Page({
  data: {
    patientName: '张明',
    diagnosis: '右膝关节置换术',
    postOpDays: 3,
    tasks: [],
    loading: false
  },

  onLoad(options) {
    if (options.patientName) this.setData({ patientName: options.patientName });
    if (options.diagnosis) this.setData({ diagnosis: options.diagnosis });
    if (options.postOpDays) this.setData({ postOpDays: parseInt(options.postOpDays) });
    this.loadTasksFromStorage();
    if (!this.hasTodayTasks()) this.generateRehabPlan();
  },

  loadTasksFromStorage() {
    const storageKey = `rehab_${this.data.patientName}_tasks`;
    const saved = wx.getStorageSync(storageKey);
    if (saved && saved.tasks && saved.date === new Date().toDateString()) {
      this.setData({ tasks: saved.tasks });
    } else {
      this.setData({ tasks: [] });
    }
  },

  hasTodayTasks() {
    const storageKey = `rehab_${this.data.patientName}_tasks`;
    const saved = wx.getStorageSync(storageKey);
    return saved && saved.tasks && saved.tasks.length > 0 && saved.date === new Date().toDateString();
  },

  generateRehabPlan() {
    this.setData({ loading: true });
    const prompt = `患者诊断：${this.data.diagnosis}，术后第${this.data.postOpDays}天。请生成今天的康复训练任务清单。以JSON数组格式返回，每个任务包含name（任务名称）和instruction（具体指导）。例如：[{"name":"踝泵运动","instruction":"用力勾脚尖再绷直，每次10秒，重复20次"}]。只输出JSON。`;
    aiChat(prompt, 'rehab_demo', 'rehab').then(res => {
      this.setData({ loading: false });
      if (res.code === 200) {
        let tasks = [];
        try {
          let jsonStr = res.answer.replace(/```json/g, '').replace(/```/g, '');
          tasks = JSON.parse(jsonStr);
          if (!Array.isArray(tasks)) throw new Error();
        } catch(e) {
          tasks = this.getDefaultTasks();
        }
        tasks = tasks.map(t => ({ ...t, completed: false }));
        const todayStr = new Date().toDateString();
        const storageKey = `rehab_${this.data.patientName}_tasks`;
        wx.setStorageSync(storageKey, { date: todayStr, tasks: tasks });
        this.setData({ tasks });
        this.saveCompletionHistory(); // 更新历史完成率
      } else {
        this.setData({ tasks: this.getDefaultTasks() });
      }
    }).catch(err => {
      console.error(err);
      this.setData({ loading: false });
      wx.showToast({ title: '生成失败，使用默认计划', icon: 'none' });
      this.setData({ tasks: this.getDefaultTasks() });
    });
  },

  getDefaultTasks() {
    return [
      { name: '踝泵运动', instruction: '用力勾脚尖再绷直，每次10秒，重复20次', completed: false },
      { name: '直腿抬高', instruction: '仰卧，抬腿30度，保持10秒，重复10次', completed: false },
      { name: '冰敷', instruction: '每次15分钟，每日3次', completed: false }
    ];
  },

  completeTask(e) {
    const index = e.currentTarget.dataset.index;
    const tasks = this.data.tasks;
    if (tasks[index].completed) return;
    tasks[index].completed = true;
    this.setData({ tasks });
    const storageKey = `rehab_${this.data.patientName}_tasks`;
    const saved = wx.getStorageSync(storageKey);
    if (saved) {
      saved.tasks = tasks;
      wx.setStorageSync(storageKey, saved);
    }
    // 保存历史记录
    this.saveCompletionHistory();
    wx.showToast({ title: '打卡成功', icon: 'success' });
  },

  saveCompletionHistory() {
    const patientName = this.data.patientName;
    const storageKey = `rehab_${patientName}_tasks`;
    const saved = wx.getStorageSync(storageKey);
    console.log('saveCompletionHistory 被调用, saved:', saved);
    if (saved && saved.tasks) {
      const total = saved.tasks.length;
      const completed = saved.tasks.filter(t => t.completed).length;
      const rate = total ? Math.floor(completed / total * 100) : 0;
      const todayStr = new Date().toDateString();
      let history = wx.getStorageSync(`history_${patientName}`) || [];
      const existingIndex = history.findIndex(h => h.date === todayStr);
      if (existingIndex >= 0) {
        history[existingIndex].rate = rate;
      } else {
        history.push({ date: todayStr, rate: rate });
      }
      history = history.slice(-7);
      wx.setStorageSync(`history_${patientName}`, history);
      console.log('历史记录已保存', history);
    } else {
      console.warn('未找到康复任务数据，无法保存历史记录');
    }
  },

  editInfo() {
    wx.showModal({
      title: '修改信息',
      content: '请输入术后天数',
      editable: true,
      placeholderText: '请输入数字',
      success: (res) => {
        if (res.confirm && res.content) {
          const days = parseInt(res.content);
          if (!isNaN(days)) {
            this.setData({ postOpDays: days });
            this.generateRehabPlan();
          }
        }
      }
    });
  },

  goToHistory() {
    wx.navigateTo({ url: '/pages/rehab/history/history' });
  },

  goToRecords() {
    wx.navigateTo({ url: '/pages/rehab/records/records' });
  }
});