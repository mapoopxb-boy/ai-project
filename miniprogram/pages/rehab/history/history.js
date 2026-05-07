Page({
  data: {
    historyData: []
  },
  onLoad() {
    this.loadHistoryData();
  },
  loadHistoryData() {
    const patientName = '张明';
    let history = wx.getStorageSync(`history_${patientName}`) || [];
    
    if (history.length === 0) {
      console.log('未找到历史数据，使用演示数据');
      history = [
        { date: '5/1', rate: 40 },
        { date: '5/2', rate: 60 },
        { date: '5/3', rate: 80 },
        { date: '5/4', rate: 70 },
        { date: '5/5', rate: 90 },
        { date: '5/6', rate: 85 },
        { date: '5/7', rate: 95 }
      ];
    }
    this.setData({ historyData: history });
    this.drawChart(history);
  },
  drawChart(history) {
    if (!history || history.length === 0) return;
    const ctx = wx.createCanvasContext('historyCanvas');
    const width = 300;
    const height = 150;
    const step = width / (history.length - 1);
    ctx.beginPath();
    ctx.moveTo(10, height - history[0].rate * height / 100);
    for (let i = 1; i < history.length; i++) {
      ctx.lineTo(10 + i * step, height - history[i].rate * height / 100);
    }
    ctx.setStrokeStyle('#07c160');
    ctx.setLineWidth(2);
    ctx.stroke();
    ctx.draw();
  }
});