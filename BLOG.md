# 블로그 운영 가이드

Jekyll 블로그입니다.
`main`에 push하면 GitHub Actions가 빌드해서 https://ohaeun.github.io/OHaEuN/ 에 배포합니다.

## 새 글 쓰기

`_posts/YYYY-MM-DD-<번호 또는 슬러그>.md` 파일을 만들고 아래 front matter를 넣습니다.

```yaml
---
title: "글 제목"
date: 2026-11-01 21:00:00 +0900
permalink: /25            # 생략하면 /글-제목 형태
category: "Front-end"     # _config.yml의 category_tree 이름, 하위는 "Front-end/GSAP"
tags: ["React", "Next.js"]
thumbnail: /assets/posts/25/01.png   # 목록 썸네일 (선택)
image: /assets/posts/25/01.png       # 공유 미리보기(og:image) (선택)
description: "검색 결과/목록에 보일 요약"
---
```

이미지는 `assets/posts/<번호>/`에 넣고 본문에서 `![](/assets/posts/25/01.png)`처럼 씁니다.

## 설정 (`_config.yml`)

- `google_analytics`: GA4 측정 ID → 방문자 수, 유입 경로(검색엔진/리퍼러), 인기 글 확인
- `goatcounter`: GoatCounter 코드 → 티스토리 통계처럼 간단한 유입 경로/리퍼러 대시보드
- `webmaster_verifications`, `naver_site_verification`: 구글 서치콘솔 / 네이버 서치어드바이저 / Bing 소유 확인
- `utterances_repo`: 댓글·방명록 (utterances 앱 설치 필요)
- `category_tree`: 카테고리 메뉴 순서

검색엔진에는 `https://ohaeun.github.io/OHaEuN/sitemap.xml`, RSS는 `https://ohaeun.github.io/OHaEuN/rss.xml`을 제출하면 됩니다.

## 로컬 미리보기

```bash
bundle install
bundle exec jekyll serve   # http://127.0.0.1:4000/OHaEuN/
```
