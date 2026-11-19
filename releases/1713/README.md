# 1713 — اتصالات و وبهوک: هر فاکتور به همان ربات خبر می‌دهد

این پوشه فقط فایل‌های لازم برای همان بلوکِ نصبی است. ربات و API بعد از اجرای
بلوک این چهار فایل را برمی‌دارند:

| فایل | مقصد |
| --- | --- |
| `conn_repo.py` | `bot/services/conn_repo.py` |
| `conn.py` | `bot/handlers/conn.py` |
| `fix4.py` | پچِ `backend/app/services/webhooks.py` و `invoices_open.py` |
| `fix5.py` | پچِ `bot/handlers/__init__.py`، `bot/keyboards.py`، `bot/handlers/late.py` |

دو فایلِ `fix` خودشان بکاپ می‌گیرند و اگر سینتکس خراب شود برمی‌گردانند.
