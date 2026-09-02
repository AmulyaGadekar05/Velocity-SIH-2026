import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace Auth Modal
auth_modal_pattern = re.compile(r'<!-- ── Auth Modal.*?</div>\s*</div>\s*</div>', re.DOTALL)
content = auth_modal_pattern.sub('', content)

# 2. Replace Navbar Auth Area
nav_auth_pattern = re.compile(r'<div id="nav-auth-area">.*?</div>', re.DOTALL)
nav_auth_jinja = """<div id="nav-auth-area" style="display: flex; gap: 10px; align-items: center;">
  {% if user %}
    <div class="user-chip" style="display: flex; align-items: center; gap: 8px;">
      <div class="user-avatar" style="width:32px; height:32px; border-radius:50%; background:var(--primary); color:white; display:flex; align-items:center; justify-content:center; font-weight:bold;">{{ user.name[:2]|upper }}</div>
      <span class="user-name">{{ user.name }}</span>
    </div>
    <a href="/logout" class="nav-cta">Logout</a>
  {% else %}
    <a href="/login" class="nav-cta">Login / Sign Up</a>
  {% endif %}
</div>"""
content = nav_auth_pattern.sub(nav_auth_jinja, content)

# 3. Replace JS AUTH object
js_auth_pattern = re.compile(r'const AUTH = \{.*?\};', re.DOTALL)
js_auth_jinja = "const AUTH = { isLoggedIn: () => {% if user %}true{% else %}false{% endif %}, userName: () => '{% if user %}{{ user.name }}{% endif %}' };"
content = js_auth_pattern.sub(js_auth_jinja, content)

# 4. Remove UI JS handlers for Auth Modals
# Just leave them or remove them carefully. Let's comment them out or let them fail gracefully if buttons aren't found.
# Better to remove the `refreshAuthUI` and listeners.
js_ui_pattern = re.compile(r'/\* ── Auth Tab Switcher.*?loginBtn\.addEventListener.*?\);', re.DOTALL)
content = js_ui_pattern.sub('/* Auth UI managed by Jinja */', content)

# 5. Remove 'Register as Worker' tab since that's handled at registration.
# (Or keep it and redirect to login if clicked). Let's remove the worker form from index.html because it's only for clients now.
worker_form_pattern = re.compile(r'<!-- ── Worker Registration Form.*?</div>\s*</div>', re.DOTALL)
content = worker_form_pattern.sub('', content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("index.html cleaned")
