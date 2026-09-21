import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'c:\Users\komma\OneDrive\Desktop\SIH\frontend\patient.html', encoding='utf-8') as f:
    content = f.read()

# ── FIX 1: Replace showScreen to use inline style (bypasses all CSS specificity) ──
old_showScreen = '''  // ── UTILITIES ──────────────────────────────
  function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById('screen-' + id).classList.add('active');
    window.scrollTo(0, 0);
  }'''

new_showScreen = '''  // ── UTILITIES ──────────────────────────────
  function showScreen(id) {
    // Hide all screens with inline style to guarantee override of any CSS
    document.querySelectorAll('.screen').forEach(s => {
      s.classList.remove('active');
      s.style.display = 'none';
    });
    // Show target screen
    const target = document.getElementById('screen-' + id);
    target.classList.add('active');
    target.style.display = 'flex';
    window.scrollTo(0, 0);
  }'''

if old_showScreen in content:
    content = content.replace(old_showScreen, new_showScreen, 1)
    print('[PASS] showScreen fixed')
else:
    print('[FAIL] showScreen not found - checking exact text...')
    idx = content.find('function showScreen')
    if idx >= 0:
        print(repr(content[idx:idx+250]))

# ── FIX 2: Wrap startChatScreen in try/catch to expose hidden JS errors ──
old_startChat = '''  // ── CHAT SCREEN INIT ─────────────────────────
  function startChatScreen() {
    showScreen('chat');
    document.getElementById('chat-patient-name').textContent = state.patientName;
    document.getElementById('chat-messages').innerHTML = '';
    state.transcriptHistory = [];
    addMessage('assistant', `Hello ${state.patientName}! 👋 I'm your AI intake assistant.\\n\\nPlease describe what brings you to the clinic today — describe your main symptoms in your own words.`);
    state.sessionId = null;
    state.summary = null;
    state.attachments = [];
    renderAttachmentThumbnails();
  }'''

new_startChat = '''  // ── CHAT SCREEN INIT ─────────────────────────
  function startChatScreen() {
    try {
      showScreen('chat');
      document.getElementById('chat-patient-name').textContent = state.patientName || 'Patient';
      document.getElementById('chat-messages').innerHTML = '';
      state.transcriptHistory = [];
      state.sessionId = null;
      state.summary = null;
      state.attachments = [];
      addMessage('assistant', `Hello ${state.patientName || 'there'}! 👋 I\\'m your AI intake assistant.\\n\\nPlease describe what brings you to the clinic today — describe your main symptoms in your own words.`);
      renderAttachmentThumbnails();
    } catch (err) {
      console.error('startChatScreen error:', err);
      toast('❌ Error loading chat: ' + err.message);
    }
  }'''

if old_startChat in content:
    content = content.replace(old_startChat, new_startChat, 1)
    print('[PASS] startChatScreen wrapped in try/catch')
else:
    print('[FAIL] startChatScreen not found exactly - trying partial match...')
    idx = content.find('function startChatScreen')
    if idx >= 0:
        print(repr(content[idx:idx+400]))

with open(r'c:\Users\komma\OneDrive\Desktop\SIH\frontend\patient.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done.')
