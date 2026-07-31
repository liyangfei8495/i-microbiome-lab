import json

files = ['content.json', 'deploy-ghpages/content.json']

competitions = [
    {
        "id": "c-2026-chitosan",
        "titleZh": "微生物源壳聚糖国创赛项目招新",
        "titleEn": "Microbe-derived Chitosan Innovation Competition — Recruitment",
        "statusZh": "火热报名中",
        "statusEn": "Open for Registration",
        "org": "主办：实验室联合创新创业学院",
        "date": "2026.07–2026.09",
        "descZh": "围绕微生物源壳聚糖的产业化应用展开，欢迎对生物制造、合成生物学感兴趣的同学报名。项目提供全程科研训练、竞赛指导与职业规划支持。",
        "descEn": "Focused on the industrial application of microbe-derived chitosan. Open to students interested in biomanufacturing and synthetic biology, with full research training, competition mentoring, and career planning support.",
        "image": ""
    },
    {
        "id": "c-2025-bio",
        "titleZh": "2025 全国大学生生物制造创新大赛",
        "titleEn": "2025 National Bio-manufacturing Innovation Contest",
        "statusZh": "已圆满结束",
        "statusEn": "Concluded",
        "org": "主办：相关学会与高校联合",
        "date": "2025.05–2025.08",
        "descZh": "本实验室团队参赛并完成答辩，展示了微生物模块化组装方向的阶段性成果。",
        "descEn": "Our lab team participated and presented progressive results in microbial modular assembly.",
        "image": ""
    }
]

for f in files:
    d = json.load(open(f, encoding='utf-8'))
    d['competitions'] = competitions
    with open(f, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
    print('已写入', f, '| 顶层字段数:', len(d))
