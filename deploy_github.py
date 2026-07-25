import os, json, subprocess, urllib.request, urllib.error

TOKEN = os.environ["GH_TOKEN"]
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
API = "https://api.github.com"
REPO = "i-microbiome-lab"
CWD = r"D:\liyangfei\lab\web\网站\team-site-admin\deploy-ghpages"


def api(method, path, data=None):
    req = urllib.request.Request(API + path, method=method, headers=HEADERS)
    if data is not None:
        req.data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(req) as r:
            return r.read().decode(), r.status
    except urllib.error.HTTPError as e:
        return e.read().decode(), e.code


# 1. 获取当前用户名
body, _ = api("GET", "/user")
login = json.loads(body)["login"]
print("GitHub 用户名:", login)

# 2. 创建公开仓库（若不存在）
body, code = api("GET", f"/repos/{login}/{REPO}")
if code == 404:
    body, code = api("POST", "/user/repos", {
        "name": REPO,
        "private": False,
        "auto_init": False,
        "description": "i-Microbiome Lab website",
    })
    print("仓库创建:", code, REPO)
else:
    print("仓库已存在，跳过创建")

# 3. git push
remote = f"https://{TOKEN}@github.com/{login}/{REPO}.git"
subprocess.run(["git", "remote", "remove", "origin"], cwd=CWD, capture_output=True)
subprocess.run(["git", "remote", "add", "origin", remote], cwd=CWD, check=True)
subprocess.run(["git", "branch", "-M", "main"], cwd=CWD, check=True)
r = subprocess.run(["git", "push", "-u", "origin", "main", "--force"],
                   cwd=CWD, capture_output=True, text=True)
print("PUSH rc=", r.returncode)
print(r.stdout[-400:])
print(r.stderr[-400:])

# 4. 开启 GitHub Pages（main 分支 / 根）
body, code = api("POST", f"/repos/{login}/{REPO}/pages",
                 {"source": {"branch": "main", "path": "/"}})
print("PAGES rc=", code, body[:200])

print("URL:", f"https://{login}.github.io/{REPO}/")
