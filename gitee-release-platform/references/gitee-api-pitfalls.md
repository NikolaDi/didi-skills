# Gitee API 实测坑（逐条展开）

以下每条都在生产环境实测踩过、验证过修法。写涉及 Gitee API 的脚本前通读一遍。

## 1. 空仓库建 Release 必 400

报错藏得深：HTTP 400，body 是「创建标签失败：<tag>」——真实原因是 Gitee 建 Release 时要自动从默认分支建 tag，空仓库没有分支可指，连默认分支都是 `None`。

**修法**：先用 contents API 推个 README 初始化仓库（公开仓库里 README 本来就该有）：

```bash
python -c "import base64,json;print(json.dumps({'content':base64.b64encode(open('README.md','rb').read()).decode(),'message':'init'}))" > payload.json
curl -X POST "https://gitee.com/api/v5/repos/<owner>/<repo>/contents/README.md?access_token=$TOKEN" \
     -H 'Content-Type: application/json' --data-binary @payload.json   # 期望 201
```

## 2. tag 不存在时建 Release 必须显式 `target_commitish`

Gitee 不会自己猜默认分支，缺了直接 400「target_commitish is missing」。**别硬编码 master**——运行时查：

```bash
DBRANCH=$(curl -s "https://gitee.com/api/v5/repos/<owner>/<repo>?access_token=$TOKEN" | 取 default_branch)
```

「删 Release 重发」正好走 tag 不存在的路径，脚本必须始终带上这个字段。

## 3. 「不存在」返回 200 + 字面量 `null`，不是 404

`GET /releases/tags/<不存在的tag>` 返回 HTTP 200、body 为字面量 `null`（空体也有）。`json.load` 得到 `None`，后续 `.get()` 在 `set -e` 脚本里直接把整个脚本带崩，而崩溃信息（AttributeError）完全看不出是 Gitee 的锅。

**修法**：解析函数必须容错——

```bash
json_field() { python -c "import json,sys
try: d = json.load(sys.stdin)
except Exception: d = None
print(d.get('$1','') if isinstance(d, dict) else '')"; }
```

## 4. 传附件的表单字段名是 `file`

不是 `attachment`（GitHub 习惯）。字段名错时 Gitee 返回 `{"messages":["file is missing"]}`。

**重命名附件**用 curl 的 `;filename=` 语法（本地文件名不动）：

```bash
curl -X POST "$API/releases/<id>/attach_files?access_token=$TOKEN" \
     -F "file=@app-debug.apk;filename=<前缀>-<版本串>.apk"
```

## 5. 验证 token 别用公开端点

仓库列表、读 Release 等匿名也能 200，「验证了个寂寞」。用：

```bash
curl -s "https://gitee.com/api/v5/user?access_token=$TOKEN"   # 返回用户 JSON = token 有效
```

## 6. 中文 notes 不走 curl argv

Windows 控制台 GBK，中文经命令行参数传给原生 curl 必炸（表现为 JSON 解析错误或 400）。**修法**：Python 生成 `ensure_ascii=True` 的载荷文件（中文转 `\uXXXX`），`--data-binary @file` 提交：

```bash
printf '%s' "$NOTES" > body.txt
python -c "import json;json.dump({'tag_name':'$TAG','name':'$TAG','prerelease':False,'target_commitish':'$DBRANCH','body':open(r'body.txt',encoding='utf-8').read()},open(r'payload.json','w'),ensure_ascii=True)"
curl -X POST "$API/releases?access_token=$TOKEN" -H 'Content-Type: application/json' --data-binary @payload.json
```

## 7. 附件无断点续传；直链是 302→CDN 带时效签名

实测对附件发 Range 请求仍返回 200 全量。20MB 整包前台下载可接受；客户端下载走 `.part` 临时文件，成功才改名，不会装到半包。

下载直链 `releases/download/<tag>/<file>` 会 302 到 `foruda.gitee.com` 的 CDN 地址（带 token/ts 签名），**不能缓存最终地址**，客户端每次从固定入口 URL 重走。

## 8. 删 Release：`DELETE /releases/{id}` → 204，tag 连带消失

重发流程：`DELETE /repos/{repo}/releases/{id}`（204）→ 直接重新 create（此时 tag 也没了，记得坑 2 的 `target_commitish`）。

## 9. Release 网页永远带源码包 zip/tar.gz，无法关闭

Gitee 自动为 Release 的 tag 生成源码归档下载。发布专用仓库按约定只放 README，源码包里就一份 README，无实害；后端接口只认 `.apk` 附件，完全不感知它。网页用户注意别下错即可。
