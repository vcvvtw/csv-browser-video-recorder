import os
import sys
import time
import math
import random
import re
import shutil
from playwright.sync_api import sync_playwright

PATH_TO_VIDEO_FOLDER = "./video"

_active_page = None
_current_cursor_x = 640.0
_current_cursor_y = 360.0

# Injected overlay: cursor, highlight, ripples, and search suggestions
INJECT_OVERLAY_SCRIPT = """
(() => {
    let container = null;
    let cursor = null;
    let highlight = null;
    let calloutBox = null;
    let suggestionsBox = null;

    function isCursorHidden() {
        try {
            return sessionStorage.getItem('__automation_cursor_hidden') === '1';
        } catch(e) {
            return false;
        }
    }

    function ensureElements() {
        const root = document.documentElement || document.body;
        if (!root) return false;

        container = document.getElementById('__automation_overlay_container');
        if (!container) {
            container = document.createElement('div');
            container.id = '__automation_overlay_container';
            container.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:2147483647;overflow:hidden;';

            cursor = document.createElement('div');
            cursor.id = '__automation_cursor';
            cursor.style.cssText = 'position:absolute;top:0;left:0;width:0;height:0;pointer-events:none;z-index:2147483647;will-change:transform;';

            highlight = document.createElement('div');
            highlight.id = '__automation_cursor_highlight';
            highlight.style.cssText = 'position:absolute;width:64px;height:64px;border-radius:50%;background:rgba(255,230,0,0.45);top:-32px;left:-32px;pointer-events:none;box-shadow:0 0 12px rgba(255,230,0,0.35);transition:transform 0.15s ease;';

            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '32');
            svg.setAttribute('height', '32');
            svg.setAttribute('viewBox', '0 0 32 32');
            svg.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;overflow:visible;filter:drop-shadow(0 2px 5px rgba(0,0,0,0.4));';

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', 'M0,0 L0,22 L5.5,16.5 L11,27.5 L14.5,25.5 L9,14.5 L17,14.5 Z');
            path.setAttribute('fill', '#FFFFFF');
            path.setAttribute('stroke', '#000000');
            path.setAttribute('stroke-width', '1.8');
            path.setAttribute('stroke-linejoin', 'round');
            path.setAttribute('stroke-linecap', 'round');

            svg.appendChild(path);
            cursor.appendChild(highlight);
            cursor.appendChild(svg);
            container.appendChild(cursor);

            calloutBox = document.createElement('div');
            calloutBox.id = '__automation_callout_box';
            calloutBox.style.cssText = 'position:fixed;top:28px;left:50%;transform:translateX(-50%);pointer-events:none;z-index:2147483646;display:flex;flex-direction:column;align-items:center;gap:10px;';
            container.appendChild(calloutBox);

            const style = document.createElement('style');
            style.id = '__automation_style';
            style.textContent = `
                @keyframes __ripple_animation {
                    0% {
                        transform: translate(-50%, -50%) scale(0.2);
                        opacity: 1;
                        border-width: 4px;
                    }
                    50% {
                        opacity: 0.85;
                        border-width: 3px;
                    }
                    100% {
                        transform: translate(-50%, -50%) scale(1.6);
                        opacity: 0;
                        border-width: 1px;
                    }
                }
                .__automation_ripple {
                    position: absolute;
                    width: 64px;
                    height: 64px;
                    border-radius: 50%;
                    border: 3px solid #FF9800;
                    background: radial-gradient(circle, rgba(255, 235, 59, 0.6) 0%, rgba(255, 152, 0, 0.25) 60%, rgba(255, 152, 0, 0) 100%);
                    box-shadow: 0 0 14px rgba(255, 152, 0, 0.8), inset 0 0 10px rgba(255, 235, 59, 0.6);
                    pointer-events: none;
                    z-index: 2147483647;
                    animation: __ripple_animation 450ms cubic-bezier(0.1, 0.8, 0.3, 1) forwards;
                }
                @keyframes __callout_enter_leave {
                    0% {
                        opacity: 0;
                        transform: translateY(-16px) scale(0.95);
                    }
                    15% {
                        opacity: 1;
                        transform: translateY(0) scale(1.0);
                    }
                    80% {
                        opacity: 1;
                        transform: translateY(0) scale(1.0);
                    }
                    100% {
                        opacity: 0;
                        transform: translateY(-12px) scale(0.95);
                    }
                }
                .__automation_callout_item {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    font-size: 16pt;
                    font-weight: 600;
                    padding: 12px 24px;
                    border-radius: 6px;
                    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
                    pointer-events: none;
                    max-width: 80vw;
                    text-align: center;
                    border: 1px solid rgba(0,0,0,0.12);
                }
            `;
            root.appendChild(style);
            root.appendChild(container);

            let ix = 640, iy = 360;
            try {
                const sx = sessionStorage.getItem('__automation_cur_x');
                const sy = sessionStorage.getItem('__automation_cur_y');
                if (sx !== null && sy !== null) {
                    ix = parseFloat(sx);
                    iy = parseFloat(sy);
                }
            } catch(e) {}
            cursor.style.transform = `translate(${ix}px, ${iy}px)`;
            cursor.style.display = isCursorHidden() ? 'none' : 'block';
        } else {
            cursor = document.getElementById('__automation_cursor');
            highlight = document.getElementById('__automation_cursor_highlight');
            calloutBox = document.getElementById('__automation_callout_box');
        }

        return true;
    }

    window.__updateCursorPos = function(x, y) {
        ensureElements();
        if (cursor) {
            cursor.style.transform = `translate(${x}px, ${y}px)`;
        }
        try {
            sessionStorage.setItem('__automation_cur_x', x);
            sessionStorage.setItem('__automation_cur_y', y);
        } catch(e) {}
    };

    window.__hideCursor = function() {
        try {
            sessionStorage.setItem('__automation_cursor_hidden', '1');
        } catch(e) {}
        ensureElements();
        if (cursor) cursor.style.display = 'none';
    };

    window.__showCursor = function() {
        try {
            sessionStorage.removeItem('__automation_cursor_hidden');
        } catch(e) {}
        ensureElements();
        if (cursor) cursor.style.display = 'block';
    };

    window.__suppressNextRipple = false;
    let lastRippleTime = 0;
    let lastRippleX = -1;
    let lastRippleY = -1;

    window.__triggerRipple = function(x, y, durationMs = 450) {
        ensureElements();
        if (!container) return;
        const now = Date.now();
        if (now - lastRippleTime < 200 && Math.hypot(x - lastRippleX, y - lastRippleY) < 15) {
            return;
        }
        lastRippleTime = now;
        lastRippleX = x;
        lastRippleY = y;

        const ripple = document.createElement('div');
        ripple.className = '__automation_ripple';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.style.animationDuration = durationMs + 'ms';
        if (cursor && cursor.parentNode === container) {
            container.insertBefore(ripple, cursor);
        } else {
            container.appendChild(ripple);
        }

        if (highlight) {
            highlight.style.transform = 'scale(0.85)';
            setTimeout(() => { if (highlight) highlight.style.transform = 'scale(1.0)'; }, Math.min(120, durationMs / 2));
        }

        setTimeout(() => {
            try { ripple.remove(); } catch(e) {}
        }, durationMs);
    };

    window.ShowCallout = function(text, bgColor = '#FFEB3B', textColor = '#000000', fade = true) {
        ensureElements();
        if (!calloutBox) return;
        const item = document.createElement('div');
        item.className = '__automation_callout_item';
        item.style.backgroundColor = bgColor;
        item.style.color = textColor;
        item.innerText = text;

        if (fade) {
            item.style.animation = '__callout_enter_leave 3.8s ease-in-out forwards';
            setTimeout(() => item.remove(), 3900);
        } else {
            item.style.opacity = '1';
        }
        calloutBox.appendChild(item);
    };

    window.addEventListener('mousemove', (e) => {
        window.__updateCursorPos(e.clientX, e.clientY);
    }, { passive: true, capture: true });

    window.addEventListener('mousedown', (e) => {
        if (window.__suppressNextRipple) {
            window.__suppressNextRipple = false;
            return;
        }
        window.__triggerRipple(e.clientX, e.clientY, 450);
    }, { passive: true, capture: true });

    // Hide cursor and clear ripples on page unload
    window.addEventListener('beforeunload', () => {
        try {
            sessionStorage.setItem('__automation_cursor_hidden', '1');
            document.querySelectorAll('.__automation_ripple').forEach(r => r.remove());
        } catch(e) {}
    });
    window.addEventListener('pagehide', () => {
        try {
            sessionStorage.setItem('__automation_cursor_hidden', '1');
            document.querySelectorAll('.__automation_ripple').forEach(r => r.remove());
        } catch(e) {}
    });

    // Search suggestions dropdown
    window.__initSmartSuggestions = function(city) {
        city = city || 'Berlin';

        // Suppress native suggestions to prevent duplicated popup
        const hideStyle = document.createElement('style');
        hideStyle.id = '__hide_raw_ddg_suggestions';
        hideStyle.textContent = `
            #searchbox-suggestions, [class*="search-dropdown-module"] {
                display: none !important;
            }
        `;
        document.head.appendChild(hideStyle);

        const input = document.querySelector('textarea[name="q"], input[name="q"]');
        if (!input || input.__smart_sugg_done) return;
        input.__smart_sugg_done = true;

        const wrap = input.closest('.search-toggle-box-module-scss-module__ul1rLa__queryWrap') || input.parentElement;
        if (!wrap) return;

        wrap.style.position = 'relative';

        let dropdown = document.getElementById('__smart_suggestions_dropdown');
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.id = '__smart_suggestions_dropdown';
            dropdown.style.cssText = `
                position: absolute;
                top: 48px;
                left: 0;
                right: 0;
                background: #FFFFFF;
                border-radius: 0 0 24px 24px;
                box-shadow: rgba(0, 0, 0, 0.06) 0px 8px 16px 0px, rgba(0, 0, 0, 0.06) 0px 2px 6px 0px, rgba(0, 0, 0, 0.08) 1px 0px 0px 0px, rgba(0, 0, 0, 0.08) -1px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 1px 0px 0px;
                padding: 4px 8px 12px;
                z-index: 10000;
                box-sizing: border-box;
                display: none;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            `;
            wrap.appendChild(dropdown);
            suggestionsBox = dropdown;
        }

        window.__renderSuggestions = function(val) {
            if (!dropdown) return;
            dropdown.innerHTML = '';
            val = (val || '').trim();

            wrap.style.borderRadius = '24px 24px 0 0';
            wrap.style.borderBottom = 'none';
            wrap.style.boxShadow = 'rgba(0, 0, 0, 0.06) 0px 2px 6px 0px, rgba(0, 0, 0, 0.08) 1px 0px 0px 0px, rgba(0, 0, 0, 0.08) -1px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px -1px 0px 0px';

            const lowerV = val.toLowerCase();
            let matched = [];

            if (!val) {
                matched = [
                    `magento developer in ${city}`,
                    `magento ecommerce agency in ${city}`,
                    `magento 2 certified expert in ${city}`,
                    `magento online shop developer`,
                    `magento migration to shopify`
                ];
            } else if (lowerV.startsWith("magento developer in")) {
                matched = [
                    `magento developer in ${city}`,
                    `magento developer in ${city} agency`,
                    `magento developer in ${city} freelance`,
                    `magento developer in ${city} certified`,
                    `magento developer in ${city} near me`
                ];
            } else if (lowerV.startsWith("magento dev")) {
                matched = [
                    `magento developer in ${city}`,
                    `magento developer agency in ${city}`,
                    `magento development company`,
                    `magento developer freelance`,
                    `magento developer salary`
                ];
            } else if (lowerV.startsWith("m")) {
                matched = [
                    `magento developer in ${city}`,
                    `magento ecommerce agency in ${city}`,
                    `magento 2 certified agency`,
                    `magento online shop developer`,
                    `magento development company near me`
                ];
            } else {
                matched = [
                    `${val} in ${city}`,
                    `${val} developer in ${city}`,
                    `${val} agency`,
                    `${val} online shop`
                ];
            }

            const list = document.createElement('div');
            list.style.cssText = 'display: flex; flex-direction: column; gap: 2px;';

            matched.slice(0, 5).forEach((text) => {
                const row = document.createElement('div');
                row.style.cssText = `
                    display: flex;
                    align-items: center;
                    height: 36px;
                    padding: 0 12px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 15px;
                    line-height: 1.2;
                    color: #222222;
                    box-sizing: border-box;
                `;
                row.onmouseenter = () => row.style.backgroundColor = '#F2F2F2';
                row.onmouseleave = () => row.style.backgroundColor = 'transparent';

                const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                icon.setAttribute('viewBox', '0 0 16 16');
                icon.setAttribute('width', '16');
                icon.setAttribute('height', '16');
                icon.setAttribute('fill', 'none');
                icon.style.cssText = 'margin-right: 12px; color: #757575; flex-shrink: 0;';
                const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                p.setAttribute('d', 'M7 0C3.134 0 0 3.134 0 7s3.134 7 7 7c1.708 0 3.273-.612 4.488-1.628l3.445 3.445c.244.244.64.244.884 0s.244-.64 0-.884l-3.445-3.445C13.388 10.273 14 8.708 14 7c0-3.866-3.134-7-7-7M1.25 7c0-3.176 2.574-5.75 5.75-5.75S12.75 3.824 12.75 7 10.176 12.75 7 12.75 1.25 10.176 1.25 7');
                p.setAttribute('fill', 'currentColor');
                p.setAttribute('fill-rule', 'evenodd');
                p.setAttribute('clip-rule', 'evenodd');
                icon.appendChild(p);
                row.appendChild(icon);

                const label = document.createElement('div');
                label.style.cssText = 'flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';

                const lowerT = text.toLowerCase();
                if (val && lowerT.startsWith(lowerV)) {
                    const match = text.slice(0, val.length);
                    const rest = text.slice(val.length);
                    label.innerHTML = `<span style="font-weight: 400; color: #222222;">${match}</span><strong style="font-weight: 700; color: #222222;">${rest}</strong>`;
                } else if (val && lowerT.includes(lowerV)) {
                    const pos = lowerT.indexOf(lowerV);
                    const before = text.slice(0, pos);
                    const match = text.slice(pos, pos + val.length);
                    const after = text.slice(pos + val.length);
                    label.innerHTML = `<span style="font-weight: 400; color: #222222;">${before}</span><span style="font-weight: 400; color: #222222;">${match}</span><strong style="font-weight: 700; color: #222222;">${after}</strong>`;
                } else {
                    label.innerHTML = `<strong style="font-weight: 700; color: #222222;">${text}</strong>`;
                }
                row.appendChild(label);
                list.appendChild(row);
            });

            dropdown.appendChild(list);

            const footer = document.createElement('div');
            footer.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 10px 8px 2px; border-top: 1px solid rgba(0,0,0,0.06); margin-top: 6px;';

            const aiWrap = document.createElement('div');
            aiWrap.style.cssText = 'display: flex; align-items: center; gap: 8px; font-size: 13px; color: #555555; font-weight: 500;';
            aiWrap.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 0L9.8 5.6L16 6.8L11.5 10.8L12.9 16L8 13.2L3.1 16L4.5 10.8L0 6.8L6.2 5.6L8 0Z" fill="#3B82F6"/></svg>
                <span>Ask Duck.ai</span>
                <span style="background: #E5E7EB; border-radius: 4px; padding: 2px 6px; font-size: 11px; color: #6B7280;">Alt+Enter</span>
            `;

            const searchBtn = document.createElement('div');
            searchBtn.id = '__footer_search_button';
            searchBtn.style.cssText = 'background: #0064E0; color: #FFFFFF; border-radius: 20px; padding: 6px 18px; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.12);';
            searchBtn.innerText = 'Search';
            searchBtn.onclick = () => {
                const topBtn = document.querySelector('.search-toggle-box-module-scss-module__ul1rLa__submitButton, button[type="submit"], [aria-label="Search"]');
                if (topBtn) topBtn.click();
            };

            footer.appendChild(aiWrap);
            footer.appendChild(searchBtn);
            dropdown.appendChild(footer);

            dropdown.style.display = 'block';
        };

        window.__hideSuggestions = function() {
            if (dropdown) dropdown.style.display = 'none';
            wrap.style.borderRadius = '24px';
            wrap.style.boxShadow = '';
            wrap.style.borderBottom = '';
        };

        input.addEventListener('focus', () => window.__renderSuggestions(input.value));
        input.addEventListener('click', () => window.__renderSuggestions(input.value));
        input.addEventListener('input', () => window.__renderSuggestions(input.value));

        document.addEventListener('click', (e) => {
            if (!wrap.contains(e.target)) {
                window.__hideSuggestions();
            }
        });
    };

    function fixDDG() {
        try {
            document.querySelectorAll('input[name="origin"], input[name="we_feature_name"], input[name="we_started_at"]').forEach(el => el.remove());
            const btn = document.querySelector('.search-toggle-box-module-scss-module__ul1rLa__submitButton, button[type="submit"], [aria-label="Search"]');
            if (btn) {
                btn.style.setProperty('width', '36px', 'important');
                btn.style.setProperty('min-width', '36px', 'important');
                btn.style.setProperty('height', '32px', 'important');
                btn.style.setProperty('min-height', '32px', 'important');
                btn.style.setProperty('opacity', '1', 'important');
                btn.style.setProperty('visibility', 'visible', 'important');
                btn.style.setProperty('pointer-events', 'auto', 'important');
                btn.style.setProperty('display', 'flex', 'important');
            }
        } catch(e) {}
    }

    if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', () => {
            ensureElements();
            fixDDG();
        });
    } else {
        ensureElements();
        fixDDG();
    }

    setInterval(() => {
        ensureElements();
        fixDDG();
    }, 150);
})();
"""


def _sanitize_filename(name):
    """Sanitize string for safe filesystem usage."""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip()
    return sanitized if sanitized else "recording"


def ShowCallout(arg1, text=None, bgColor="#FFEB3B", textColor="#000000", fade=True):
    """
    Display a floating notification banner on the page.
    Supports both ShowCallout(page, text, ...) and ShowCallout(text, ...).
    """
    global _active_page
    if hasattr(arg1, "evaluate"):
        target_page = arg1
        actual_text = text if text is not None else ""
    else:
        target_page = _active_page
        actual_text = str(arg1)
        if text is not None and isinstance(text, str) and (text.startswith("#") or text.startswith("rgb")):
            textColor = bgColor if bgColor != "#FFEB3B" else "#000000"
            bgColor = text

    if target_page:
        try:
            target_page.evaluate(
                "([t, bg, tc, f]) => { if (window.ShowCallout) window.ShowCallout(t, bg, tc, f); }",
                [actual_text, bgColor, textColor, bool(fade)],
            )
        except Exception:
            pass


def smooth_move_to(page, target_x, target_y, duration=0.8, steps=48):
    """Smoothly moves cursor to (target_x, target_y) using cubic easing and natural arc."""
    global _current_cursor_x, _current_cursor_y
    dx = float(target_x) - _current_cursor_x
    dy = float(target_y) - _current_cursor_y
    dist = math.hypot(dx, dy)
    if dist < 1.0:
        page.mouse.move(target_x, target_y)
        _current_cursor_x, _current_cursor_y = float(target_x), float(target_y)
        return

    nx = -dy / dist
    ny = dx / dist
    arc_height = min(22.0, dist * 0.10) * random.choice([1.0, -1.0])

    num_steps = max(35, min(60, steps))
    step_delay = max(0.010, duration / num_steps)

    for i in range(1, num_steps + 1):
        t = i / num_steps
        ease = 4.0 * t * t * t if t < 0.5 else 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0
        arc = math.sin(math.pi * t) * arc_height
        x = _current_cursor_x + dx * ease + nx * arc
        y = _current_cursor_y + dy * ease + ny * arc
        page.mouse.move(x, y)
        time.sleep(step_delay)

    _current_cursor_x, _current_cursor_y = float(target_x), float(target_y)
    page.mouse.move(_current_cursor_x, _current_cursor_y)


def human_click(page, x, y, duration=0.45):
    """Moves to (x, y), triggers click ripple effect, and performs click."""
    smooth_move_to(page, x, y)
    duration_ms = int(duration * 1000)
    try:
        page.evaluate(
            """([cx, cy, d]) => {
                if (window.__triggerRipple) window.__triggerRipple(cx, cy, d);
                window.__suppressNextRipple = true;
            }""",
            [x, y, duration_ms],
        )
    except Exception:
        pass
    page.mouse.click(x, y)
    time.sleep(duration + 0.05)


def type_human_like(page, text):
    """Types text character-by-character with slight delays and updates suggestions."""
    words = text.split(" ")
    typed_so_far = ""

    for w_idx, word in enumerate(words):
        for ch in word:
            typed_so_far += ch
            page.keyboard.type(ch)
            try:
                page.evaluate("val => { if (window.__renderSuggestions) window.__renderSuggestions(val); }", typed_so_far)
            except Exception:
                pass
            time.sleep(random.uniform(0.07, 0.15))

        if w_idx < len(words) - 1:
            typed_so_far += " "
            page.keyboard.type(" ")
            try:
                page.evaluate("val => { if (window.__renderSuggestions) window.__renderSuggestions(val); }", typed_so_far)
            except Exception:
                pass
            time.sleep(random.uniform(0.18, 0.30))

    time.sleep(0.8)


def CaptureVideo_Magento(
    url,
    company_name,
    language,
    country,
    postcode,
    city,
    street,
    house_no,
):
    """
    Automates a browser search scenario for a given company and city,
    recording the session to a 1280x720 .webm video.

    Returns the absolute path to the generated video file, or None on error.
    """
    global _active_page, _current_cursor_x, _current_cursor_y

    os.makedirs(PATH_TO_VIDEO_FOLDER, exist_ok=True)

    playwright = None
    browser = None
    context = None
    target_video_path = None

    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = browser.new_context(
            record_video_dir=PATH_TO_VIDEO_FOLDER,
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1",
            },
        )

        context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
        context.add_init_script(INJECT_OVERLAY_SCRIPT)

        page = context.new_page()
        _active_page = page
        _current_cursor_x = 640.0
        _current_cursor_y = 360.0

        try:
            page.evaluate("() => { try { sessionStorage.removeItem('__automation_cursor_hidden'); } catch(e) {} }")
        except Exception:
            pass

        # Open page and locate search input
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        search_box = None
        for sel in ['textarea[name="q"]', 'input[name="q"]', '[name="q"]']:
            try:
                el = page.wait_for_selector(sel, state="visible", timeout=10000)
                if el:
                    search_box = el
                    break
            except Exception:
                continue

        if not search_box:
            raise RuntimeError("Could not find search input on page")

        # Configure suggestions for target city
        try:
            page.evaluate(f"city => {{ if (window.__initSmartSuggestions) window.__initSmartSuggestions(city); }}", city)
        except Exception:
            pass

        time.sleep(0.5)

        # Initial notification banner
        callout_text = f"Searching for {company_name} in {city}"
        ShowCallout(page, callout_text, bgColor="#FFEB3B", textColor="#000000", fade=True)
        time.sleep(1.8)

        # Focus search box
        box_rect = search_box.bounding_box()
        if not box_rect:
            raise RuntimeError("Search box bounding box is not available")

        box_center_x = box_rect["x"] + box_rect["width"] / 2
        box_center_y = box_rect["y"] + box_rect["height"] / 2
        human_click(page, box_center_x, box_center_y)

        # Show initial suggestions
        try:
            page.evaluate("() => { if (window.__renderSuggestions) window.__renderSuggestions(''); }")
        except Exception:
            pass
        time.sleep(0.6)

        # Type search query
        search_query = f"Magento developer in {city}"
        type_human_like(page, search_query)

        # Locate submit button
        submit_btn = None
        for sel in [
            'form button[type="submit"]',
            'button[type="submit"]',
            'input[type="submit"]',
            '[aria-label="Search"]',
        ]:
            try:
                el = page.query_selector(sel)
                if el:
                    bb = el.bounding_box()
                    if bb and bb["height"] > 0:
                        submit_btn = el
                        break
            except Exception:
                continue

        if not submit_btn:
            submit_btn = page.wait_for_selector('button[type="submit"], input[type="submit"]', timeout=4000)

        btn_rect = submit_btn.bounding_box()
        btn_center_x = btn_rect["x"] + (btn_rect["width"] / 2 if btn_rect["width"] > 0 else 16)
        btn_center_y = btn_rect["y"] + btn_rect["height"] / 2

        smooth_move_to(page, btn_center_x, btn_center_y)

        # Trigger ripple and close dropdown
        try:
            page.evaluate(
                """([cx, cy]) => {
                    if (window.__triggerRipple) window.__triggerRipple(cx, cy, 450);
                    if (window.__hideSuggestions) window.__hideSuggestions();
                    window.__suppressNextRipple = true;
                }""",
                [btn_center_x, btn_center_y],
            )
        except Exception:
            pass

        # Allow ripple animation to complete before page unload
        time.sleep(0.48)
        page.mouse.click(btn_center_x, btn_center_y)
        time.sleep(0.5)

        # Wait for search results to render
        first_result = None
        target_box = None
        poll_start = time.time()

        while time.time() - poll_start < 35:
            try:
                for sel in [
                    'a[data-testid="result-title-a"]',
                    '.react-results--main a[href^="http"]',
                    'li[data-layout="organic"] a[href^="http"]',
                    'article a[href^="http"]',
                    'h2 a[href^="http"]',
                ]:
                    candidate = page.query_selector(sel)
                    if candidate and candidate.is_visible():
                        c_box = candidate.bounding_box()
                        if c_box and c_box["width"] > 0 and c_box["height"] > 0:
                            first_result = candidate
                            target_box = c_box
                            break
                if first_result:
                    break
            except Exception:
                pass
            time.sleep(0.4)

        if not first_result or not target_box:
            raise RuntimeError("Search results did not load in time")

        # Re-enable cursor and announce first result
        try:
            page.evaluate("() => { if (window.__showCursor) window.__showCursor(); }")
        except Exception:
            pass

        ShowCallout(page, "Opening first result...", bgColor="#FFEB3B", textColor="#000000", fade=True)
        time.sleep(1.2)

        res_x = target_box["x"] + target_box["width"] / 2
        res_y = target_box["y"] + target_box["height"] / 2

        smooth_move_to(page, res_x, res_y)

        try:
            page.evaluate(
                """([cx, cy]) => {
                    if (window.__triggerRipple) window.__triggerRipple(cx, cy, 450);
                    window.__suppressNextRipple = true;
                }""",
                [res_x, res_y],
            )
        except Exception:
            pass

        time.sleep(0.48)
        page.mouse.click(res_x, res_y)
        time.sleep(0.6)

        # Keep page open for recording
        try:
            page.wait_for_load_state("domcontentloaded", timeout=12000)
        except Exception:
            pass
        time.sleep(3.5)

        # Finalize and save video
        video_obj = page.video
        context.close()
        raw_video_path = video_obj.path() if video_obj else None
        browser.close()
        playwright.stop()
        playwright = None
        browser = None
        context = None

        if not raw_video_path or not os.path.exists(raw_video_path):
            raise RuntimeError("Recorded video file was not found")

        safe_name = _sanitize_filename(company_name)
        target_video_path = os.path.join(PATH_TO_VIDEO_FOLDER, f"{safe_name}.webm")

        if os.path.abspath(raw_video_path) != os.path.abspath(target_video_path):
            if os.path.exists(target_video_path):
                try:
                    os.remove(target_video_path)
                except Exception:
                    pass
            shutil.move(raw_video_path, target_video_path)

        return os.path.abspath(target_video_path)

    except Exception as e:
        sys.stderr.write(f"Error in CaptureVideo_Magento for '{company_name}': {e}\n")
        return None

    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass
