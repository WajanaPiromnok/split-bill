# ภาพรวมระบบ SplitBill

Frontend ใช้ Next.js, TypeScript และ Tailwind CSS ครับ เวลาใช้งาน browser จะเรียก FastAPI โดยตรง แล้ว backend ตรวจสิทธิ์กับกฎการแบ่งเงินก่อนอ่านหรือบันทึก PostgreSQL

- [เปิดแผนภาพ HTML และสลับธีม](stack.html)
- [ภาพพื้นสว่าง](stack.png) · [ภาพพื้นมืด](stack-dark.png)
- [วิธีติดตั้งและรัน](../../README.md) · [ภาพหน้าจอแอปจริง](../../design-system/README.md)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="stack-dark.png">
  <img alt="ภาพรวม SplitBill: Next.js เรียก FastAPI และ PostgreSQL โดยแยก setup กับ CI ไว้อีกส่วน" src="stack.png">
</picture>

## แต่ละส่วนทำอะไร

| ส่วน | ใช้อะไร | หน้าที่ |
| --- | --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS | เลือกผู้ใช้และกลุ่ม กรอกบิล ดูส่วนแบ่ง ยอดสุทธิและรายการบิล รวมถึงลบบิลของผู้จ่าย |
| API | FastAPI, Uvicorn, Python 3.12+ | รับ HTTP/JSON ตรวจรูปแบบ request และอ่าน `X-User` มีครบ 6 endpoints ตามโจทย์ |
| Business rules | Python `Decimal` และจำนวนเต็มหน่วยสตางค์ | ตรวจสมาชิก แบ่ง equal/exact เช็คยอดรวม คีย์ซ้ำและสิทธิ์ลบ |
| Data access | SQLAlchemy 2, psycopg 3 | query และ transaction กับ PostgreSQL |
| ฐานข้อมูลแอป | PostgreSQL 16 | เก็บผู้ใช้ กลุ่ม สมาชิก บิลและส่วนแบ่ง ใช้ `NUMERIC(12,2)` สำหรับเงิน |
| Setup | Alembic และ seed script | สร้าง schema และข้อมูลตัวอย่าง รัน seed ซ้ำได้ |
| API contract | OpenAPI และ [เอกสาร API](../api-contract.md) | ดูรูปแบบ request, response และ error ให้ frontend ใช้ตรงกัน |
| CI | GitHub Actions สอง workflows | ตรวจ backend และ frontend รวมถึง browser ที่เชื่อม API จริง |
| ฐานข้อมูลทดสอบ | PostgreSQL 16 แยกอีก database | แต่ละรอบสร้าง schema ชั่วคราว แล้วลบเมื่อจบ |

กล่อง `backend/` ในภาพเป็นแอป Python เดียว ส่วน routing, services และ repositories เป็นไฟล์ที่แบ่งหน้าที่ภายในแอปครับ

## เวลาส่งบิลเกิดอะไรขึ้น

1. Frontend คำนวณ preview ด้วย `BigInt` หน่วยสตางค์ แล้วส่งเงินเป็น string เช่น `"100.00"` พร้อม `X-User` และ `Idempotency-Key`
2. FastAPI ตรวจ request จากนั้น service เช็คว่าคนส่ง คนจ่าย และคนที่หารอยู่ในกลุ่มหรือไม่
3. Equal split แจกเศษสตางค์ตามลำดับสมาชิก ส่วน exact split ต้องรวมได้เท่ายอดบิล
4. Repository บันทึกบิลกับส่วนแบ่งใน transaction เดียว ฐานข้อมูลบังคับไม่ให้มีคีย์ซ้ำในกลุ่มเดียวกัน ถ้าส่งซ้ำ API จะคืนบิลเดิม
5. Frontend โหลดรายการบิลและยอดสุทธิใหม่จาก API ยอดสุทธิคิดจากเงินที่จ่ายลบส่วนแบ่งของตัวเอง โดยไม่รวมบิลที่ soft delete แล้ว

Browser เรียก backend ข้าม origin จึงกำหนด origin ที่อนุญาตไว้ใน `CORS_ORIGINS` ส่วน `X-User` ใช้เลือกผู้ใช้ตัวอย่างตามโจทย์ ยังไม่มีระบบบัญชีหรือ login แบบ production

## Setup กับการทดสอบ

เส้นทึบในภาพคือการเรียกข้อมูลตอนใช้งาน ส่วนเส้นประคือคำสั่ง setup และการทดสอบ Alembic กับ seed ติดต่อฐานข้อมูลโดยตรงก่อนเริ่มใช้งานแอป

[Backend workflow](../../.github/workflows/backend.yml) ตรวจ Ruff, OpenAPI, migrations, seed และ pytest ส่วน [Frontend workflow](../../.github/workflows/frontend.yml) ตรวจ ESLint, TypeScript, Node tests และ production build แล้วรัน Chromium ผ่าน Next.js, FastAPI และ PostgreSQL 16 จริง การทดสอบ browser ใช้ข้อมูลใน schema ชั่วคราวตาม [integration runner](../../scripts/test-frontend-integration.py)

โค้ดแบ่งเป็น `main`, `dev/backend` และ `dev/frontend` ตาม [Git workflow](../git-workflow.md) โดยส่ง milestone เข้า `main` ผ่าน PR แล้ว sync กลับสอง dev branches ภาพแสดงโครงสร้างระบบ ส่วนผล CI ต้องดูจาก commit ที่ส่งมอบ ยังไม่ได้เลือก hosting หรือ cloud vendor ครับ

## ไฟล์และแหล่งภาพ

`stack.html` ฝังโลโก้กับฟอนต์ไว้แล้ว เปิด offline ได้ ภาพ `stack.png` และ `stack-dark.png` render จาก HTML เดียวกันด้วย headless Chromium ที่ความละเอียด 2 เท่า ถ้าแก้แผนภาพ ให้สร้าง PNG ใหม่ทั้งสองธีมด้วย

ใช้โลโก้เดิมของแต่ละโครงการโดยไม่เปลี่ยนสี Alembic ใช้เครื่องหมาย SQLAlchemy ส่วน browser ใช้ pictogram ของ template รายละเอียดแหล่งที่มาและ license อยู่ใน [NOTICE.txt](NOTICE.txt)
