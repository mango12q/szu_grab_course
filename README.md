# szu_grab_course

深圳大学抢课脚本（Python 3），命令行运行，配置好之后 `python main.py` 即可开始抢课。

- 原始项目：[Lewin671/YourLesson](https://github.com/Lewin671/YourLesson)
- 维护版：[guiyi886/szu_grab_course](https://github.com/guiyi886/szu_grab_course)（本项目基于它）
- 本仓库：[mango12q/szu_grab_course](https://github.com/mango12q/szu_grab_course)

> ⚠️ 抢课脚本会造成高频请求，请自己控制好 `delay`、遵守学校的选课规定，被风控或封号后果自负。

---

## 一、环境要求

| 项目 | 要求 |
| --- | --- |
| Python | 3.8 以上即可，**已在 Python 3.13.9 实测通过** |
| 第三方库 | 只有一个：`requests` |
| 操作系统 | Windows / macOS / Linux 都行 |

> ❗ **不要照抄旧版 README 里的依赖清单**（`requests==2.21.0`、`urllib3==1.24.1` 那套）。
> 那些 2019 年的包在 Python 3.12+ 上连 `import` 都会失败：
> `ModuleNotFoundError: No module named 'urllib3.packages.six.moves'`。
> 本项目代码是纯 Python 3 语法，用任意现代版本的 requests 即可。

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

1. 先在网页上登录选课系统，按 `F12` 打开开发者工具，切到 **网络 / Network** 面板。
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

## 五、运行

```bash
python main.py
```

`main.py` 会按 `courses` 从上到下、循环 `count` 轮地提交选课请求，
每轮里每个课程之间间隔 `delay` 毫秒；出现「抢课成功」后停止，最后打印当前已选中的课程。

中途想停就按 `Ctrl+C`。

![示意图](./pic/示意图6.png)

## 六、常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| `ModuleNotFoundError: No module named 'urllib3.packages.six.moves'` | 装了旧版 requests，执行 `pip install -U requests` |
| `ModuleNotFoundError: No module named 'requests'` | 没装依赖，执行 `pip install -r requirements.txt` |
| 提示「还没填写：cookie、token、…」 | `config.json` 没建或没填全 |
| 一直返回登录页 / 报错 | Cookie 和 token 过期了，重新登录后重新抓一遍（每次登录都会变） |
| 提示「该课程超过课容量」 | 课满了，脚本会继续重试，等有人退课 |
| 课程 id 提交后无效 | id 里带的是学年学期码（`20232024…`），过了学期就失效，需要重新获取 |
| `data/` 里的 csv 变空了 | 跑过 `download_data.py`，它每次都会先清空再下载 |

## 七、说明

- 本仓库只是把公共代码整理成「别人 clone 下来就能跑」的状态：补了 `requirements.txt`，
  把学号 / Cookie / token 从 `setting.py` 挪到不参与版本控制的 `config.json`。
- 抢课逻辑本身来自原项目，未做改动，也没有在任何真实选课批次里验证过。
- 目录结构：

```
main.py              抢课入口
setting.py           配置读取 + 请求头
choose_course.py     选课 / 查询已选课程
downloads.py         课程列表下载逻辑
download_data.py     课程列表下载入口
util.py              session / 时间戳 / url 拼接
login.py             Cookie、token 获取（未被 main.py 调用）
data/                下载下来的课程 csv
pic/                 README 用的截图
config.example.json  配置模板 → 复制成 config.json 填自己的信息
```
