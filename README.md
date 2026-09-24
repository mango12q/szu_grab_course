# szu_grab_course

深圳大学抢课脚本（Python 3），命令行运行，配置好之后 `python main.py` 即可开始抢课。

- 反馈：**优先提 [Issue](https://github.com/mango12q/szu_grab_course/issues)**，或发邮件到 **mango12q@163.com**

> ⚠️ 抢课脚本会造成高频请求，请自己控制好 `delay`、遵守学校的选课规定，被风控或封号后果自负。

---

## 一、环境要求

| 项目 | 要求 |
| --- | --- |
| Python | 3.8 以上即可，**已在 Python 3.13.9 实测通过** |
| 第三方库 | 只有一个：`requests` |
| 操作系统 | Windows / macOS / Linux 都行 |

## 二、下载

```bash
git clone https://github.com/mango12q/szu_grab_course.git
cd szu_grab_course
```

不想用 git 的话，在 GitHub 页面点 `Code → Download ZIP` 解压也一样。

## 三、安装依赖

```bash
pip install -r requirements.txt
```

> macOS / Linux 上如果提示 `python: command not found`，把本文档所有命令里的 `python`
> 换成 `python3`（用 `python3 -m pip install -r requirements.txt` 装依赖）。

## 四、配置

复制配置模板，然后在 `config.json` 里填自己的信息：

```bash
# Windows
copy config.example.json config.json
# macOS / Linux
cp config.example.json config.json
```

`config.json` 已被 `.gitignore` 忽略，**不会被提交到 GitHub**，所以你的学号和 Cookie 不会泄露。
（不使用 `config.json`、直接改 `setting.py` 里的默认值也可以，但那样有误提交的风险。）

需要填的四个字段，全部来自浏览器 F12：

1. 先在浏览器打开 **<http://bkxk.szu.edu.cn/>** 登录选课系统，按 `F12` 打开开发者工具，切到 **网络 / Network** 面板。
2. 在页面上点一下「方案内课程」，再点「本班课程」，会看到一个 `recommendedCourse.do` 请求。
3. 点开它：
   - **请求标头（Request Headers）** 里复制 `Cookie` 和 `token` → 填到 `cookie`、`token`（这两个每次重新登录都会变）。
   - **载荷（Payload）** 里复制 `studentCode` 和 `electiveBatchCode` → 填到 `user_id`、`electiveBatchCode`。

   ![示意图](./pic/示意图1.png)
   ![示意图](./pic/示意图2.png)
   ![示意图](./pic/示意图3.png)

4. 要抢哪些课，填在 `courses` 里。两种获取课程 id 的方法：

   **方法一**：运行下面的命令把课程列表拉到 `data/` 文件夹，再从 csv 里抄 id 到 `config.json`。

   ```bash
   python download_data.py
   ```

   > 注意：这个脚本会**先清空 `data/` 目录下的所有文件**，然后再重新下载。

   ![示意图](./pic/示意图4.png)

   **方法二**：直接 F12，`Ctrl+Shift+C` 选中要选的课，在源码里看课程 id。

   ![示意图](./pic/示意图5.png)

   `type` 字段对应关系：本班课程 `TJKC`、方案内课程 `FANKC`、方案外课程 `FAWKC`、
   校公选课 `XGXK`、慕课 `MOOC`、辅修课程 `FXKC`、体育课程 `TYKC`。

   照这个格式填进 `config.json`（`id` 和 `type` 必填，`name` 只是打印给你自己看的）：

   ```json
   "courses": [
     {"id": "202320242150294000101", "type": "FANKC", "name": "信息检索(潘微科)"}
   ]
   ```

## 五、运行

**第一次配置完之后，先跑一次只读自检**（只读，不提交任何选课请求，可以放心跑）：

```bash
python check.py
```

它会依次检查：配置填全了没 → 选课系统连得上吗 → 你填的 Cookie / token 还有效吗 →
「已选课程」接口返回的字段名和程序预期的是否对得上。全打 `[OK]` 再往下走。

然后正式开始抢课：

```bash
python main.py
```

运行逻辑：

- 按 `courses` 从上到下轮询提交，每轮里每门课之间间隔 `delay` 毫秒，最多循环 `count` 轮。
- **抢到一门课就把它从待抢列表里移除，继续抢剩下的**，全部抢到才结束。
- **成功判定是两级的**：学校提示「添加选课志愿成功」或「已经选过」只算**候选**，
  程序会立刻回查学校的「已选课程」列表（最多 3 次、每次间隔 1 秒），
  按教学班 ID 精确匹配，**确认列表里真有这门课才算抢到**。
  列表里没有 → 可能只是「受理了但没落库」的假成功，这门课会**留在待抢列表里继续抢**。
- 见过的响应原文会写进 `logs/responses-日期.log`（每种响应只记一次），方便事后核对判定规则。
- 请求出错（超时 / 断网）不会中断程序，会按 0.4s → 0.8s → 1.6s ……（上限 30 秒）退避后重试。
- 如果服务器返回的是登录页，说明 Cookie / token 失效了，程序会**立刻停止**并提示你重新抓，
  不会白白跑一整晚。
- 结束时打印抢到 / 没抢到的清单，再查一次当前选课结果。

中途想停就按 `Ctrl+C`，会照常打印上面的总结。

退出码：`0` 正常结束、`1` 配置没填好、`2` 登录状态失效。

![示意图](./pic/示意图6.png)

## 六、常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| `ModuleNotFoundError: No module named 'requests'` | 没装依赖，执行 `pip install -r requirements.txt` |
| 想先确认自己配置对不对 | 跑 `python check.py`，只读自检，不会提交任何选课请求 |
| 提示「还没填写：cookie、token、…」 | `config.json` 没建或没填全 |
| 一直返回登录页 / 报错 | Cookie 和 token 过期了，重新登录后重新抓一遍（每次登录都会变） |
| 提示「该课程超过课容量」 | 课满了，脚本会继续重试，等有人退课 |
| 课程 id 提交后无效 | id 里带的是学年学期码（`20232024…`），过了学期就失效，需要重新获取 |
| `data/` 里的 csv 变空了 | 跑过 `download_data.py`，它每次都会先清空再下载 |
| 提示「检测到登录状态已失效」后退出 | Cookie / token 过期了，重新登录后重抓一遍（退出码 2） |
| 一直提示「请求出错 … 后重试」 | 网络不通，或 `config.json` 里课程 id / `type` 填错了；连续 5 次出错会额外提示 |
| 卡在一个请求上不动 | 不会了，所有请求都有 10 秒默认超时（`util.py` 里的 `TIMEOUT` 可调） |
| 提示「已选课程列表里还没有这门课，继续重试」 | 可能只是已选列表同步延迟，也可能是「受理了没落库」的假成功；程序会自动继续抢 |
| 提示「找不到可用于比对的课程 ID 字段，无法核实」 | 学校已选列表的字段名和预期不同；看一眼 `logs/` 里的 `enrolled_list` 原文就能确认 |

## 七、说明

- 学号 / Cookie / token 写在 `config.json` 里（已被 `.gitignore` 忽略，不会提交）；也可以直接改
  `setting.py` 里的默认值，但那样有误提交的风险。
- 几个容易踩坑的地方，程序里都做了处理：
  - 抢到一门课就从待抢列表移除、继续抢剩下的，不会重复提交同一门课，`courses` 里后面的课
    也不会被前面的课挡住。
  - 请求出错（超时、断网）会按 0.4s → 0.8s → 1.6s ……（上限 30 秒）退避后再试，
    不会在网络故障时毫无间隔地猛发请求。
  - 所有请求都有 10 秒默认超时，服务器不响应时不会永久卡死。
  - 结束前查询选课结果那一步失败，只提示，不影响前面已经抢到的课程。
  - 抢课成功采用两级确认：提交回执只算候选，必须回查「已选课程」列表、按教学班 ID 精确匹配
    才计入已抢到；查不到就留在待抢列表继续抢。已选列表里虽然有课、但一个可用的 ID 字段都没有
    时，会降级为信任提交回执并明确告警（响应原文在 `logs/` 里）。
  - 见过的响应原文会落盘到 `logs/`（已 gitignore），方便用真实响应校准判定规则。
- 以上逻辑是用模拟响应做的离线验证，**没有在任何真实选课批次里验证过**。
- 目录结构：

```
main.py              抢课入口（轮询、两级确认、退避重试、结果汇总）
check.py             只读自检（配置 / 连通性 / 登录态 / 接口字段名），不提交选课请求
setting.py           配置读取 + 请求头
choose_course.py     选课提交 / 查询已选课程（两级确认用的回查接口）
downloads.py         课程列表下载逻辑
download_data.py     课程列表下载入口
util.py              session（带 10 秒默认超时）/ 时间戳 / url 拼接 / 登录页判断
logs/                运行日志 + 见过的响应原文（gitignore，不进仓库）
data/                下载下来的课程 csv
pic/                 README 用的截图
config.example.json  配置模板 → 复制成 config.json 填自己的信息
```

## 八、反馈与联系方式

用这个脚本遇到问题、发现 bug，或者想提改进建议：

- **优先提 Issue**：<https://github.com/mango12q/szu_grab_course/issues>（公开提，别人也能看到结论）
- 不方便公开的话，发邮件到 **mango12q@163.com**

为了能快点定位问题，请附上：

- 你的 Python 版本（`python --version`）和操作系统
- 完整的报错输出（把终端里的内容整段复制下来）
- `logs/` 里对应的响应原文——如果是「判定抢课成功」这类问题，这一段最关键

> ⚠️ 不要把 `config.json` 发出来，里面有你的学号和 Cookie。`logs/` 里的响应原文一般不含个人信息，
> 但发之前也建议自己扫一眼。
