(function () {
  'use strict';

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var escapeHtml = function (s) {
    return String(s || '').replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  /* ── Theme ─────────────────────────────────────────────────────── */
  $$('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var dark = document.documentElement.dataset.theme !== 'dark';
      if (dark) document.documentElement.dataset.theme = 'dark';
      else delete document.documentElement.dataset.theme;
      try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (e) {}
    });
  });

  /* ── Header shadow, progress bar, back-to-top ──────────────────── */
  var header = $('.site-header');
  var bar = $('.progress span');
  var toTop = $('[data-to-top]');
  var article = $('.post-content');
  function onScroll() {
    var y = window.scrollY;
    if (header) header.classList.toggle('is-scrolled', y > 4);
    if (toTop) toTop.classList.toggle('is-visible', y > 600);
    if (bar && article) {
      var start = article.offsetTop - window.innerHeight * 0.3;
      var end = article.offsetTop + article.offsetHeight - window.innerHeight;
      var pct = Math.min(1, Math.max(0, (y - start) / Math.max(1, end - start)));
      bar.style.width = (pct * 100) + '%';
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  if (toTop) toTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });

  /* ── Post content enhancements ─────────────────────────────────── */
  if (article) {
    // Collapse the empty "spacer" paragraphs that came from the old editor.
    $$('p', article).forEach(function (p) {
      if (!p.children.length && !p.textContent.replace(/[\s ]/g, '')) p.classList.add('spacer');
    });

    // Tables scroll horizontally on small screens.
    $$('table', article).forEach(function (t) {
      if (t.parentElement.classList.contains('table-wrap')) return;
      var wrap = document.createElement('div');
      wrap.className = 'table-wrap';
      t.parentNode.insertBefore(wrap, t);
      wrap.appendChild(t);
    });

    // Video attachments play inline.
    $$('figure.fileblock a[href$=".mp4"]', article).forEach(function (a) {
      var v = document.createElement('video');
      v.src = a.getAttribute('href');
      v.controls = true;
      v.preload = 'metadata';
      v.playsInline = true;
      a.parentNode.insertBefore(v, a);
    });

    // Toggle blocks.
    $$("div[data-ke-type='moreLess'] .btn-toggle-moreless", article).forEach(function (btn) {
      btn.setAttribute('role', 'button');
      btn.setAttribute('tabindex', '0');
      var box = btn.closest("div[data-ke-type='moreLess']");
      if (btn.parentElement.tagName === 'P') btn.parentElement.classList.add('moreless-toggle-row');
      var toggle = function (e) {
        e.preventDefault();
        box.classList.toggle('open');
        btn.textContent = box.classList.contains('open') ? (box.dataset.textLess || '접기') : (box.dataset.textMore || '더보기');
      };
      btn.addEventListener('click', toggle);
      btn.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') toggle(e); });
    });

    // Code: highlight, language label, copy button.
    var highlight = function () {
      $$('pre > code', article).forEach(function (code) {
        if (window.hljs && !code.classList.contains('hljs')) window.hljs.highlightElement(code);
        var pre = code.parentElement;
        if ($('.code-toolbar', pre)) return;
        var lang = (code.className.match(/language-([\w-]+)/) || [])[1] || (code.result && code.result.language) || '';
        var bar = document.createElement('div');
        bar.className = 'code-toolbar';
        bar.innerHTML = (lang ? '<span class="code-lang">' + escapeHtml(lang) + '</span>' : '') +
          '<button type="button" class="code-copy">복사</button>';
        pre.appendChild(bar);
        $('.code-copy', bar).addEventListener('click', function (e) {
          var btn = e.currentTarget;
          navigator.clipboard.writeText(code.innerText).then(function () {
            btn.textContent = '복사됨!';
            setTimeout(function () { btn.textContent = '복사'; }, 1500);
          });
        });
      });
    };
    if (window.hljs) highlight();
    else window.addEventListener('load', highlight);

    // Image lightbox.
    article.addEventListener('click', function (e) {
      var img = e.target.closest('figure img');
      if (!img || img.closest('a')) return;
      var box = document.createElement('div');
      box.className = 'lightbox';
      box.innerHTML = '<img alt="">';
      box.firstChild.src = img.currentSrc || img.src;
      var close = function () { box.remove(); document.removeEventListener('keydown', onKey); };
      var onKey = function (ev) { if (ev.key === 'Escape') close(); };
      box.addEventListener('click', close);
      document.addEventListener('keydown', onKey);
      document.body.appendChild(box);
    });

    // Table of contents with heading anchors and scroll-spy.
    var headings = $$('h2, h3, h4', article).filter(function (h) { return h.textContent.trim() && !h.closest('.moreless-content'); });
    var toc = $('[data-toc]');
    var used = {};
    headings.forEach(function (h) {
      if (!h.id) {
        var base = h.textContent.trim().toLowerCase().replace(/[^\w가-힣]+/g, '-').replace(/^-+|-+$/g, '') || 'section';
        var id = base, n = 1;
        while (used[id] || document.getElementById(id)) id = base + '-' + (++n);
        h.id = id;
      }
      used[h.id] = true;
      var anchor = document.createElement('a');
      anchor.className = 'heading-anchor';
      anchor.href = '#' + h.id;
      anchor.setAttribute('aria-label', '이 섹션 링크');
      anchor.textContent = '#';
      h.appendChild(anchor);
    });
    if (toc && headings.length >= 2) {
      var list = $('[data-toc-list]', toc);
      var minDepth = Math.min.apply(null, headings.map(function (h) { return +h.tagName[1]; }));
      headings.forEach(function (h) {
        var li = document.createElement('li');
        li.className = 'depth-' + (+h.tagName[1] - minDepth + 2);
        var a = document.createElement('a');
        a.href = '#' + h.id;
        a.textContent = h.textContent.replace(/#$/, '').trim();
        li.appendChild(a);
        list.appendChild(li);
      });
      toc.hidden = false;
      var links = $$('a', list);
      var spy = function () {
        var current = 0;
        headings.forEach(function (h, i) { if (h.getBoundingClientRect().top < 120) current = i; });
        links.forEach(function (a, i) { a.classList.toggle('is-active', i === current); });
      };
      window.addEventListener('scroll', spy, { passive: true });
      spy();
    }
  }

  /* ── Search ────────────────────────────────────────────────────── */
  var indexPromise;
  function loadIndex() {
    if (!indexPromise) {
      var decoder = document.createElement('textarea');
      var decode = function (s) { decoder.innerHTML = s || ''; return decoder.value.replace(/\u00a0/g, ' '); };
      indexPromise = fetch(window.BLOG.searchIndex).then(function (r) { return r.json(); }).then(function (posts) {
        posts.forEach(function (p) { p.content = decode(p.content); p.description = decode(p.description); });
        return posts;
      });
    }
    return indexPromise;
  }

  function search(posts, q) {
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    return posts.map(function (p) {
      var title = p.title.toLowerCase();
      var meta = ((p.category || '') + ' ' + (p.tags || []).join(' ')).toLowerCase();
      var body = (p.content || '').toLowerCase();
      var score = 0;
      for (var i = 0; i < terms.length; i++) {
        var t = terms[i];
        var s = (title.indexOf(t) !== -1 ? 10 : 0) + (meta.indexOf(t) !== -1 ? 5 : 0) + (body.indexOf(t) !== -1 ? 1 : 0);
        if (!s) return null;
        score += s;
      }
      return { post: p, score: score };
    }).filter(Boolean).sort(function (a, b) { return b.score - a.score; }).map(function (r) { return r.post; });
  }

  function mark(text, q) {
    var safe = escapeHtml(text);
    q.split(/\s+/).filter(Boolean).forEach(function (t) {
      var re = new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
      safe = safe.replace(re, '<mark>$1</mark>');
    });
    return safe;
  }

  function snippet(p, q) {
    var body = p.content || '';
    var t = q.split(/\s+/)[0].toLowerCase();
    var i = body.toLowerCase().indexOf(t);
    if (i < 0) return p.description || '';
    var start = Math.max(0, i - 30);
    return (start ? '…' : '') + body.slice(start, i + 90);
  }

  var modal = $('[data-search-modal]');
  var input = $('[data-search-input]');
  var results = $('[data-search-results]');
  var active = 0;

  function renderResults(q) {
    loadIndex().then(function (posts) {
      var found = search(posts, q).slice(0, 12);
      active = 0;
      if (!q.trim()) { results.innerHTML = ''; return; }
      if (!found.length) { results.innerHTML = '<li class="search-empty">‘' + escapeHtml(q) + '’에 대한 결과가 없어요</li>'; return; }
      results.innerHTML = found.map(function (p, i) {
        return '<li' + (i === 0 ? ' class="is-active"' : '') + '><a href="' + p.url + '">' +
          '<span class="sr-title">' + mark(p.title, q) + '</span>' +
          '<span class="sr-meta">' + escapeHtml([p.category, p.date].filter(Boolean).join(' · ')) + '</span>' +
          '<span class="sr-snippet">' + mark(snippet(p, q), q) + '</span></a></li>';
      }).join('');
    });
  }

  function setActive(i) {
    var items = $$('li', results).filter(function (li) { return li.querySelector('a'); });
    if (!items.length) return;
    active = (i + items.length) % items.length;
    items.forEach(function (li, j) { li.classList.toggle('is-active', j === active); });
    items[active].scrollIntoView({ block: 'nearest' });
  }

  function openSearch() {
    if (!modal) return;
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    input.value = '';
    results.innerHTML = '';
    setTimeout(function () { input.focus(); }, 0);
    loadIndex();
  }
  function closeSearch() {
    if (!modal) return;
    modal.hidden = true;
    document.body.style.overflow = '';
  }

  $$('[data-search-open]').forEach(function (b) { b.addEventListener('click', openSearch); });
  $$('[data-search-close]').forEach(function (b) { b.addEventListener('click', closeSearch); });
  if (input) {
    input.addEventListener('input', function () { renderResults(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setActive(active + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(active - 1); }
      else if (e.key === 'Enter') {
        var a = $('li.is-active a', results);
        if (a) location.href = a.href;
        else if (input.value.trim()) location.href = window.BLOG.searchIndex.replace(/search\.json$/, 'search') + '?q=' + encodeURIComponent(input.value.trim());
      }
    });
  }
  document.addEventListener('keydown', function (e) {
    var typing = /input|textarea|select/i.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
    if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !typing)) {
      e.preventDefault();
      modal.hidden ? openSearch() : closeSearch();
    } else if (e.key === 'Escape' && modal && !modal.hidden) {
      closeSearch();
    }
  });
  if (!/Mac|iPhone|iPad/.test(navigator.platform)) {
    $$('.search-trigger kbd').forEach(function (k) { k.textContent = 'Ctrl K'; });
  }

  // Full search results page (/search?q=...).
  var pageResults = $('[data-search-page-results]');
  if (pageResults) {
    var q = (new URLSearchParams(location.search).get('q') || '').trim();
    $('[data-search-page-input]').value = q;
    if (q) {
      $('[data-search-page-title]').textContent = '‘' + q + '’ 검색 결과';
      loadIndex().then(function (posts) {
        var found = search(posts, q);
        $('[data-search-page-count]').textContent = found.length + '개의 글';
        pageResults.innerHTML = found.map(function (p) {
          return '<li class="post-row"><a href="' + p.url + '"><div class="post-row-body">' +
            '<div class="post-row-meta">' + (p.category ? '<span class="post-row-cat">' + escapeHtml(p.category.split('/').pop()) + '</span>' : '') +
            '<time>' + escapeHtml(p.date) + '</time></div>' +
            '<h3 class="post-row-title">' + mark(p.title, q) + '</h3>' +
            '<p class="post-row-excerpt">' + mark(snippet(p, q), q) + '</p></div>' +
            (p.thumbnail ? '<div class="post-row-thumb"><img loading="lazy" src="' + p.thumbnail + '" alt=""></div>' : '') +
            '</a></li>';
        }).join('') || '<li class="search-empty">검색 결과가 없어요</li>';
      });
    }
  }
})();
