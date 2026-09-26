# 换项目复用清单与参考实现

## 复用清单

- [ ] Gitee 建公开仓库，README 初始化（见 gitee-api-pitfalls.md 坑 1）
- [ ] 个人访问令牌（projects 权限），只在本地使用
- [ ] 后端 env 加发布仓库名（如 `APP_RELEASE_GITEE_REPO=<owner>/<repo>`）并重启
- [ ] 服务端照抄本页「解析器」与「视图」，settings 加 `APP_RELEASE_GITEE_REPO`（或改名的等价配置）与缓存 TTL
- [ ] 客户端构建脚本照抄本页「版本号 git 派生」（gradle/mk/xcodebuild 同理）
- [ ] 客户端升级判断照抄本页「一致性判断」；「以后再说」去重键用版本串
- [ ] `scripts/upload_release.sh` 复制到新项目，按头注释配环境变量

## 参考实现 1：服务端解析器（Python，仅依赖 requests）

```python
GITEE_API = 'https://gitee.com/api/v5'

def fetch_latest_release(repo, timeout=5):
    """GET /repos/{repo}/releases/latest（匿名）。失败返回 None，由调用方降级到旧缓存。"""
    try:
        resp = requests.get(f'{GITEE_API}/repos/{repo}/releases/latest', timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None

def parse_release(data):
    """tag 即版本串、.apk 附件即安装包、body 即更新说明；无效返回 None。"""
    if not isinstance(data, dict):
        return None
    apk_url = next((a.get('browser_download_url')
                    for a in (data.get('assets') or [])
                    if isinstance(a, dict) and str(a.get('browser_download_url') or '').lower().endswith('.apk')), None)
    if not apk_url:
        return None
    tag = str(data.get('tag_name') or '')
    version_name = tag[1:] if tag.startswith('v') else tag
    if not version_name:
        return None
    notes_lines = (line.strip() for line in str(data.get('body') or '').splitlines())
    return {'version_name': version_name, 'apk_url': apk_url,
            'notes': '\n'.join(line for line in notes_lines if line)}
```

## 参考实现 2：检查接口视图（Django/DRF 风格，匿名 + 内存缓存）

```python
_release_cache = {'data': None, 'fetched_at': 0.0}   # monotonic 计时

class AppReleaseView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.APP_RELEASE_GITEE_REPO:
            return Response(status=204)
        now = monotonic()
        stale = now - _release_cache['fetched_at'] >= settings.APP_RELEASE_CACHE_TTL   # 600s
        if _release_cache['data'] is None or stale or request.query_params.get('fresh'):
            parsed = parse_release(fetch_latest_release(settings.APP_RELEASE_GITEE_REPO))
            if parsed:
                _release_cache['data'] = parsed      # 拉取失败时保留旧缓存（Gitee 挂了也能服务）
                _release_cache['fetched_at'] = now
        return Response(_release_cache['data']) if _release_cache['data'] else Response(status=204)
```

## 参考实现 3：客户端版本号 git 派生（Android gradle.kts）

```kotlin
fun git(vararg args: String): String = try {
    ProcessBuilder("git", *args).start().inputStream.bufferedReader().readText().trim()
} catch (_: Exception) { "" }

fun gitVersionName(root: File): String {
    val rawTag = git("describe", "--tags", "--abbrev=0")
    val count = if (rawTag.isEmpty()) git("rev-list", "--count", "HEAD")
                else git("rev-list", "$rawTag..HEAD", "--count")
    val hash = git("rev-parse", "--short=6", "HEAD").ifEmpty { "unknown" }
    val date = git("log", "-1", "--date=format:%y%m%d", "--format=%cd").ifEmpty { "unknown" }
    val dirty = git("status", "--porcelain").isNotEmpty()
    val tag = rawTag.removePrefix("v").ifEmpty { "none" }
    return "$tag.${count.ifEmpty { "0" }}-$hash-$date${if (dirty) "-x" else ""}"
}

defaultConfig {
    // versionName = "<tag剥v>.<count>-<hash6>-<YYMMDD>[-x]"
    versionName = gitVersionName(rootDir)
    // versionCode = 全量提交数，随提交单调递增，发版零手工维护
    versionCode = git("rev-list", "--count", "HEAD").toIntOrNull() ?: 1
}
```

口径同嵌入式 `mk/git_ver.mk`。tag 只打基线段（如 `v1.0`），第三段由 count 提供——若在 HEAD 上打 `v1.0.1` 这类三段 tag 会拼出冗余的 `1.0.1.0-...`。

## 参考实现 4：客户端升级判断（Kotlin 纯函数）

```kotlin
object Version {
    /** 版本串不一致即有新版本（含回滚/脏树 -x 场景）；远端空 = 无数据不提示 */
    fun isUpdateAvailable(localVersion: String, remoteVersion: String): Boolean =
        remoteVersion.isNotEmpty() && remoteVersion != localVersion
}
```

- 检查：`BuildConfig.VERSION_NAME` vs 服务端 `version_name`
- 「以后再说」：DataStore/SharedPreferences 存版本串做去重键（别用 versionCode 整数）
- 下载：`.part` 临时文件，`contentLength` 校验完整后改名为 `<前缀>-<versionName>.apk`，FileProvider 拉系统安装器

## 服务端回归用例要点

- body 无约定行/缺 `.apk` 附件/空 tag → 解析返回 None（接口 204）
- 正常样例 → 200 且三个字段逐字相等
- Gitee 挂（fetch 返回 None）→ 有旧缓存则继续 200 服务旧数据，无缓存则 204
- 未配置仓库 → 204
