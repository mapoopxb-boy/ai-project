// Node.js v25+ 需要 localstorage-file 路径以兼容 miniprogram-ci
process.env.NODE_OPTIONS = process.env.NODE_OPTIONS || '';
if (!process.env.NODE_OPTIONS.includes('--localstorage-file')) {
  process.env.NODE_OPTIONS += ' --localstorage-file=/tmp/miniprogram-storage.json';
}

const ci = require('miniprogram-ci');
const path = require('path');
const fs = require('fs');

// 自动将 ENV 设置为 'prod'（确保上传体验版使用云端地址）
const requestJsPath = path.join(__dirname, 'utils/request.js');
try {
  let content = fs.readFileSync(requestJsPath, 'utf8');
  // 匹配当前 ENV 声明（支持 'dev' 或 "dev"）
  content = content.replace(/const ENV\s*=\s*['"]dev['"];/, "const ENV = 'prod';");
  fs.writeFileSync(requestJsPath, content, 'utf8');
  console.log('✅ request.js 环境已切换为 prod');
} catch (err) {
  console.error('❌ 切换 request.js 环境失败:', err.message);
  process.exit(1);
}

// !!! 请将这些配置替换为你自己的实际信息 !!!
const projectConfig = {
  appid: 'wx8590603022781f4e',
  type: 'miniProgram',
  projectPath: path.join(__dirname), // 项目路径，无需修改，就是当前目录
  privateKeyPath: path.join(__dirname, 'private.wx8590603022781f4e.key'), // 你刚刚下载的密钥文件路径
  ignores: ['node_modules/**/*'],
};

const version = `1.0.0-${Date.now()}`; // 自动生成唯一版本号
const desc = 'feat: 自动部署 - 用药提醒功能';
const robot = 1; // 使用机器人1进行上传

const project = new ci.Project(projectConfig);

ci.upload({
  project,
  version,
  desc,
  robot,
  setting: {
    es6: true,        // 开启ES6转ES5
    minify: true,     // 开启压缩代码
  },
  onProgressUpdate: console.log,
})
.then(() => {
  console.log(`✅ 上传成功！版本号：${version}，描述：${desc}`);
})
.catch(err => {
  console.error('❌ 上传失败:', err);
});
