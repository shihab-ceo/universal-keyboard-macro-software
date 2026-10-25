# MacroKeys — Universal Keyboard Macro

Windows-এর সাধারণ কীবোর্ডকে শর্টকাট ও ম্যাক্রো ট্রিগারে রূপ দেওয়ার ডেস্কটপ prototype। এটি Python-এর Tkinter UI, Windows `WH_KEYBOARD_LL` keyboard hook, `WH_MOUSE_LL` mouse hook এবং `SendInput` ব্যবহার করে; কোনো তৃতীয় পক্ষের Python package লাগে না।

## চালু করা

1. Windows-এ Python 3 ইনস্টল থাকতে হবে (Tkinter-সহ)।
2. `run_macrokeys.bat` চালান, অথবা `python macro_keyboard.py` চালান।
3. **ম্যাক্রো** পাতায় **নতুন ম্যাক্রো তৈরি** চাপুন। নাম লিখে output key বাছুন, অথবা **রেকর্ড শুরু** করে কীবোর্ডে sequence চাপুন। **রেকর্ড বন্ধ** চাপলে capture থামবে। মাঝের delay মিলিসেকেন্ডে সেট করুন।
4. **সেভ করে চালানোর key বাছুন** চাপার পর পূর্ণ keyboard layout-এ target key click করুন—সঙ্গে সঙ্গে assign হবে এবং macro engine চালু হবে। একই macro একাধিক trigger key-তে বসাতে চাইলে প্রতিটি key-তে আলাদা করে click করুন। চাইলে ম্যাক্রো টেনে key-এর উপর ছাড়ুন।
5. সেভ করা macro-গুলো প্রথম পাতার তালিকায় দেখা যাবে; প্রতিটি ম্যাক্রোর সব trigger key-ও তালিকায় দেখাবে। তালিকা থেকে macro বেছে আরও key যোগ করতে বা মুছতে পারবেন। **Advanced** পাতায় পুরোনো action editor, recording, import/export আছে।
6. বরাদ্দ করা trigger key-গুলো অ্যাপ চালুর পর নিজে থেকেই সক্রিয় হবে। সাময়িকভাবে থামাতে মূল screen-এর উপরের **ম্যাক্রো বন্ধ করুন** বোতাম চাপুন; আবার চালাতে **ম্যাক্রো চালু করুন** চাপুন।
7. Windows startup থেকে MacroKeys চালাতে **কম্পিউটার চালুর সাথে চালু** checkbox দিন। বন্ধ করতে checkbox সরিয়ে দিন। Startup থেকে শুরু হলে অ্যাপটি system tray-তে মিনিমাইজ হবে।

Window-এর **X** বা minimize করলে অ্যাপটি system tray-তে লুকায়; tray icon-এ left-click করলে window ফেরে, right-click করলে Open/Pause/Resume/Exit menu আসে। Windows 11 icon-টি `^` hidden-icons overflow-এ রাখতে পারে।

## Windows EXE তৈরি

Python 3.15 এবং Tkinter-এর সঙ্গে `pip install -r requirements-build.txt` চালিয়ে `build_exe.bat` চালান। `dist\MacroKeys.exe` তৈরি হবে। EXE চালাতে Python ইনস্টল দরকার নেই। EXE-র profile `%LOCALAPPDATA%\MacroKeys\profiles.json`-এ সংরক্ষিত হয়।

## Action syntax

```text
TEXT:Hello, world!
KEY:CTRL+SHIFT+S
WAIT:250
CLICK:LEFT
MOVE:500,300
SCROLL:DOWN
OPEN:https://example.com
REPEAT:3
```

`REPEAT:n` প্রথম লাইনে থাকলে বাকি sequence n বার চলে (সর্বোচ্চ 1000)। `WAIT` মিলিসেকেন্ডে হয়; সর্বোচ্চ 60,000 ms। **Select keys**-এর delay 0–60,000 ms; এটি নির্বাচিত key-গুলোর মাঝখানে যোগ হয়। `CLICK`-এ `LEFT`, `RIGHT`, `MIDDLE`; `SCROLL`-এ `UP`, `DOWN`; `OPEN`-এ application path, file path বা URL দিন। `KEY`-এ `CTRL+SHIFT+S`-এর মতো combination; `KEYDOWN`/`KEYUP` দিয়ে key state আলাদা করে পাঠানো যায়। `DISABLE` trigger key-কে আটকে রাখে, কোনো output পাঠায় না।

`Record input` keyboard key-down/key-up, mouse button down/up, wheel scroll এবং event-গুলোর মাঝের millisecond delay রেকর্ড করে। রেকর্ডিংয়ে mouse pointer movement এখনো ধরা হয় না।

প্রোফাইল ও ম্যাপিংগুলো একই ফোল্ডারের `profiles.json`-এ থাকে। `Import`/`Export` দিয়ে JSON profile আনা-নেওয়া যায়। Profile-এর Auto-switch executable ঘরে `photoshop.exe`-এর মতো process name দিলে foreground app অনুযায়ী profile বদলায়; ফাঁকা রাখলে সেই profile manual থাকে।

## বর্তমান সংস্করণের সীমা

- Low-level hook সব কীবোর্ড event দেখে; নির্দিষ্ট USB/Wireless device আলাদা করে বাছাই করে না। Per-device শনাক্তকরণের জন্য Raw Input-ভিত্তিক সংস্করণ প্রয়োজন।
- এই সংস্করণে Windows startup, dark/light switch, clipboard paste এবং toggle/hold loop mode নেই। `MOVE:x,y` action দিয়ে নির্দিষ্ট screen coordinate-এ pointer সরানো যায়, তবে recorder mouse movement ধরে না।
- Macro trigger key আটকানো হয়; অন্য কীগুলো সাধারণভাবে pass-through হয়। Injected macro output hook থেকে বাদ থাকে, যাতে macro নিজের output আবার trigger না করে।
- Shortcut পাঠানো app-এর অনুমতি/সুরক্ষা সীমা অতিক্রম করে না। কিছু elevated বা protected app-এ hook/injection কাজ নাও করতে পারে।
- এই prototype Python-এ লেখা, SRS-এ সুপারিশ করা C#/.NET বা C++ নয়। এই কম্পিউটারে .NET SDK নেই; Python runtime আছে। তাই <5 ms latency এবং background-এ <50 MB RAM লক্ষ্য এখনো মাপা বা নিশ্চিত করা হয়নি।

## নিরাপদে ব্যবহার

অজানা sequence-এ trigger key বরাদ্দ করবেন না। ম্যাক্রো চলার সময় বন্ধ করতে **Stop macros** চাপুন; দীর্ঘ sequence-এর জন্য `WAIT` ও repeat সীমা বুঝে ব্যবহার করুন।
