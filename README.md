# SplitBill

SplitBill เป็นเว็บแบ่งค่าใช้จ่ายในกลุ่มครับ ใส่ว่าใครจ่าย ใครหาร แล้วดูได้ว่าแต่ละคนต้องรับผิดชอบเท่าไหร่ และตอนนี้ใครต้องได้รับเงินคืนหรือจ่ายคืน

ผมใช้ FastAPI กับ PostgreSQL สำหรับ backend และ Next.js, TypeScript, Tailwind CSS สำหรับ frontend เรื่องที่ตั้งใจทำให้ตรงตั้งแต่แรกคือยอดเงินต้องไม่หายไปแม้แต่สตางค์เดียว กดส่งซ้ำแล้วต้องไม่เกิดบิลซ้ำ และคนที่ไม่อยู่ในกลุ่มต้องเข้าถึงข้อมูลไม่ได้

## ทำอะไรได้แล้วบ้าง

หน้าแรกให้เลือก `alice`, `bob`, `carol` หรือ `dan` ก่อน จากนั้นแสดงเฉพาะกลุ่มของคนนั้น ถ้ามีกลุ่มเดียวจะเข้าให้เลย ถ้ามีหลายกลุ่มจะให้เลือกจากหน้า "กลุ่มของฉัน"

ในกลุ่มเพิ่มบิลได้ทั้งหารเท่ากันและกำหนดจำนวนเอง มีส่วนแบ่งให้ดูก่อนบันทึก ถ้ายอด exact ยังไม่ตรงกับบิล ปุ่มบันทึกจะกดไม่ได้ ด้านข้างเป็นยอดสุทธิของสมาชิก และด้านล่างเป็นรายการค่าใช้จ่ายล่าสุด คนที่จ่ายเงินจะเห็นปุ่มลบบิลของตัวเอง

| API | ใช้ทำอะไร |
| --- | --- |
| `GET /groups` | ดูกลุ่มของผู้ใช้ที่ส่ง request |
| `GET /groups/{group_id}` | ดูชื่อกลุ่มและสมาชิก |
| `POST /groups/{group_id}/expenses` | เพิ่มค่าใช้จ่าย |
| `GET /groups/{group_id}/expenses` | ดูค่าใช้จ่าย เรียงรายการใหม่ก่อน |
| `DELETE /groups/{group_id}/expenses/{expense_id}` | ลบค่าใช้จ่าย เฉพาะคนที่จ่าย |
| `GET /groups/{group_id}/balances` | ดูยอดสุทธิของสมาชิกแต่ละคน |

รายละเอียด request, response และ error อยู่ใน [API contract](docs/api-contract.md) และ [OpenAPI schema](docs/openapi.json) หรือเปิด `/docs` ตอนรัน backend ได้เลย

## ภาพรวมระบบ

Browser เรียก FastAPI ตรงผ่าน HTTP/JSON แล้ว backend ตรวจสิทธิ์และกฎของบิลก่อนบันทึกลง PostgreSQL ส่วน Alembic กับ seed รันตอนเตรียมระบบ การทดสอบใช้ฐานข้อมูลแยกจากข้อมูลที่เปิดใช้งานในแอป

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/architecture/stack-dark.png">
  <img alt="ภาพรวม SplitBill: Next.js เรียก FastAPI และ PostgreSQL พร้อม migration, seed และ GitHub Actions" src="docs/architecture/stack.png">
</picture>

[เปิดแผนภาพ HTML แบบ offline](docs/architecture/stack.html) · [ภาพพื้นสว่าง](docs/architecture/stack.png) · [ภาพพื้นมืด](docs/architecture/stack-dark.png) · [คำอธิบายระบบ](docs/architecture/README.md)

| ส่วน | ที่ใช้ |
| --- | --- |
| หน้าเว็บ | Next.js, React, TypeScript, Tailwind CSS |
| API | Python 3.12 ขึ้นไป, FastAPI, Uvicorn |
| ฐานข้อมูล | PostgreSQL 16, SQLAlchemy 2, psycopg 3 |
| เตรียม schema | Alembic และ Python seed script |
| ตรวจงาน | pytest, Ruff, ESLint, TypeScript, Node tests และ Playwright กับ PostgreSQL จริง |
| CI | GitHub Actions |

ไฟล์หลักในโปรเจกต์อยู่ประมาณนี้ครับ

```text
backend/
  splitbill/      API, business rules, data access และ seed
  alembic/       migrations
  tests/         pytest รวมเคสที่ใช้ PostgreSQL จริง
frontend/
  app/           หน้าเว็บ ฟอร์ม และ styles
  lib/           API client, คำนวณเงิน และ pending request
scripts/         คำสั่งตรวจ backend และทดสอบทั้งระบบ
docs/            API contract, architecture และแผนพัฒนา
design-system/   แบบอ้างอิงและภาพจากแอปจริง
AI_NOTES.md      การใช้ AI, ข้อผิดพลาดที่พบ และวิธีตรวจแก้
```

## เตรียมเครื่อง

- Python 3.12 ขึ้นไป ตัวอย่างคำสั่งใช้ `python3.12` ถ้าเครื่องมี 3.13 หรือใหม่กว่าให้เปลี่ยนชื่อคำสั่งตามที่ติดตั้ง
- PostgreSQL 16 ที่รันอยู่ พร้อมบัญชีที่สร้าง role และ database ได้
- Node.js 24 LTS หรือเวอร์ชันที่โปรเจกต์รองรับในช่วง 24 ถึง 26, npm และ Git

รอบนี้ตัวเต็มอยู่บน `dev/frontend` จึง clone branch นี้ได้ก่อนที่ผมจะรวม PR เข้า `main`

```sh
git clone --branch dev/frontend https://github.com/WajanaPiromnok/split-bill.git
cd split-bill
cp .env.example .env
chmod 600 .env
```

Repository ยังเป็น private จึงต้องมีสิทธิ์อ่านก่อน clone ค่าใน `.env.example` เป็น placeholder ให้ตั้งรหัสของเครื่องตัวเองใน `.env` ซึ่งอยู่ใน `.gitignore`

## เตรียม PostgreSQL

เปิด `psql` ด้วยบัญชี admin ของ PostgreSQL ที่ใช้อยู่ แล้วสร้าง role และฐานข้อมูลสองตัว ฐานแรกเก็บข้อมูลแอป ส่วนอีกฐานใช้ทดสอบ

```psql
CREATE ROLE splitbill LOGIN;
\password splitbill
CREATE DATABASE splitbill OWNER splitbill;
CREATE DATABASE splitbill_test OWNER splitbill;
```

`\password` จะถามรหัสโดยไม่แสดงค่าที่พิมพ์ ดูวิธีใช้ใน [คู่มือ psql](https://www.postgresql.org/docs/16/app-psql.html#APP-PSQL-META-COMMAND-PASSWORD) ถ้ามี role และ database แล้วให้ใช้ของเดิมได้ และเปลี่ยนรหัสผ่าน `\password splitbill` เมื่อจำเป็น

แก้ `.env` ให้ username, password, host, port และชื่อฐานตรงกับเครื่อง โดยใช้รหัสเดียวกับที่เพิ่งตั้ง ถ้ารหัสมีอักขระพิเศษ เช่น `@`, `:` หรือ `/` ต้อง percent-encode ส่วนรหัสใน URL ก่อน

| ตัวแปร | ใช้กับอะไร |
| --- | --- |
| `DATABASE_URL` | ฐานข้อมูลแอป ใช้ scheme `postgresql+psycopg://` |
| `TEST_DATABASE_URL` | ฐานทดสอบ PostgreSQL 16 ที่แยกจากแอป |
| `CORS_ORIGINS` | origin ของ frontend ที่อนุญาต ค่าเริ่มต้นคือ `http://localhost:3000` |

Backend อ่าน `.env` ที่ root ของ repository ถ้ามี environment variable ชื่อเดียวกันใน terminal ค่านั้นจะมีผลก่อน `.env` หลังเปลี่ยนค่าต้องเริ่ม backend ใหม่

## รัน backend

จาก root ของ repository ติดตั้งตาม lock file ก่อน

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock
backend/.venv/bin/python -m pip install --no-deps -e './backend[dev]'
```

จากนั้นสร้างตาราง ใส่ข้อมูลตัวอย่าง และเปิด API

```sh
cd backend
.venv/bin/alembic upgrade head
.venv/bin/python -m splitbill.seed
.venv/bin/uvicorn splitbill.app:app --reload
```

API อยู่ที่ `http://127.0.0.1:8000` ดู Swagger ได้ที่ `http://127.0.0.1:8000/docs` และ schema ปัจจุบันที่ `/openapi.json`

Seed มีผู้ใช้ `alice`, `bob`, `carol`, `dan` และสองกลุ่มนี้ รัน seed ซ้ำได้โดยไม่สร้างสมาชิกซ้ำ

| กลุ่ม | ชื่อ | สมาชิก |
| --- | --- | --- |
| `1` | Chiang Mai trip | alice, bob, carol |
| `2` | Office lunch | bob, dan |

ลองอ่านกลุ่มผ่าน terminal ได้ดังนี้

```sh
curl -i -H 'X-User: alice' http://127.0.0.1:8000/groups
curl -i -H 'X-User: alice' http://127.0.0.1:8000/groups/1
curl -i -H 'X-User: alice' http://127.0.0.1:8000/groups/2
```

สองคำสั่งแรกจะได้กลุ่มของ Alice ส่วนคำสั่งสุดท้ายได้ `404` เพราะ Alice ไม่อยู่กลุ่ม 2 ถ้าไม่ส่ง `X-User` หรือส่งชื่อที่ไม่มีจะได้ `401`

ลองเพิ่มบิล `100.00` ที่ Alice จ่ายและหารสามคนได้ด้วยคำสั่งนี้

```sh
curl -i -X POST http://127.0.0.1:8000/groups/1/expenses \
  -H 'X-User: alice' \
  -H 'Idempotency-Key: dinner-example-001' \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "มื้อเย็นกับเพื่อน",
    "paid_by": "alice",
    "amount": "100.00",
    "split": {
      "type": "equal",
      "members": ["alice", "bob", "carol"]
    }
  }'
```

ครั้งแรกได้ `201` และ shares เป็น `33.34`, `33.33`, `33.33` ตามลำดับ ถ้าลองคำสั่งเดิมด้วย key เดิมอีกครั้งจะได้บิลเดิมกับ `200` ถ้าเป็นบิลใหม่ให้เปลี่ยน key ด้วย

ถ้าจะลองเพิ่มอีกบิลแบบกำหนดจำนวนเอง ให้เปลี่ยน `Idempotency-Key` เป็น `dinner-example-002` และใช้ค่านี้แทนค่า `split` ใน body เดิม ส่วนแบ่งต้องรวมได้ `100.00`

```json
{ "type": "exact", "shares": { "alice": "50.00", "bob": "30.00", "carol": "20.00" } }
```

ดูตัวอย่าง response และ error ของแต่ละกรณีใน [API contract](docs/api-contract.md)

## รัน frontend

เปิด terminal อีกอัน จาก root ของ repository แล้วรัน

```sh
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

เปิด `http://localhost:3000` แล้วเลือกผู้ใช้ได้เลย ค่า `NEXT_PUBLIC_API_URL` ใน `frontend/.env.local` ชี้ไป `http://127.0.0.1:8000` ถ้าเปลี่ยนพอร์ตหรือที่อยู่ API ให้แก้ค่านี้และเริ่ม Next ใหม่ ส่วน backend ต้องอนุญาต origin ของหน้าเว็บใน `CORS_ORIGINS` ด้วย

ไฟล์ config ของ frontend มีเฉพาะ URL ของ API รหัสฐานข้อมูลเก็บไว้ใน `.env` ที่ root เท่านั้น

Browser จำผู้ใช้ไว้ในแท็บเดิม เมื่อรีเฟรชคนที่มีหลายกลุ่มจะกลับมาหน้า "กลุ่มของฉัน" ปุ่ม "เปลี่ยนผู้ใช้" ใช้กลับไปเลือกชื่ออีกครั้ง ถ้ามีร่างบิล ระบบถามก่อนทิ้งร่าง ส่วนบิลที่ยังไม่รู้ว่าส่งสำเร็จหรือไม่จะเก็บ user, group, body และ key เดิมไว้เพื่อส่งซ้ำ แม้จะรีเฟรชก็กลับมารายการนั้นได้

[แนวทาง UI](DESIGN.md), [แผน frontend](docs/frontend-plan.md) และ [ภาพอ้างอิง](design-system/README.md) มีรายละเอียดเพิ่มเติม ภาพตัวอย่างด้านล่างมาจากแอปจริงกับข้อมูลจำลองใน schema ทดสอบที่แยกไว้

![หน้า SplitBill บน desktop](design-system/frontend-desktop.png)

[ดูภาพ mobile](design-system/frontend-mobile.png)

## วิธีคิดเรื่องเงิน

ผมส่งจำนวนเงินผ่าน API เป็น string เช่น `"1000.00"` แล้วใช้ `Decimal` ใน Python และ `NUMERIC(12,2)` ใน PostgreSQL เพื่อเก็บค่าถึงหน่วยสตางค์ ฝั่ง frontend แปลง string เป็นจำนวนเต็มหน่วยสตางค์ด้วย `BigInt` แล้วค่อยจัดรูปแบบเป็น `1,000.00` ตอนแสดงผล วิธีนี้ทำให้ `0.10 + 0.20` ได้ `0.30` โดยไม่ผ่าน `float`, `Number` หรือ `parseFloat` ในการคำนวณเงิน

บิลต้องมากกว่า `0` และไม่เกิน `9999999999.99` รับเลข ASCII แบบปกติที่มีทศนิยมไม่เกินสองตำแหน่ง ความยาวไม่เกิน 64 ตัวอักษร ค่าอย่าง `"10.005"` จะถูกปฏิเสธก่อนเก็บลงฐานข้อมูล ส่วนแบ่งของสมาชิกเป็น `0.00` ได้ และ API ส่งเงินกลับเป็น string สองตำแหน่งเสมอ

เวลาหารเท่ากัน ผมคำนวณในหน่วยสตางค์ด้วยผลหารกับเศษ แล้วแจกเศษทีละสตางค์ตามลำดับสมาชิกใน request เช่น `100.00` ให้ Alice, Bob, Carol จะได้ `33.34`, `33.33`, `33.33` ถ้าเป็น `1000.00` จะได้ `333.34`, `333.33`, `333.33` รวมเท่าบิลพอดี Frontend ใช้ลำดับเดียวกันจึง preview ตรงกับ backend

Exact split ตรวจผลรวมก่อนบันทึก ถ้ายังไม่ตรง frontend จะแสดงยอดที่ขาดหรือเกินและปิดปุ่มบันทึก ฝั่ง backend ตรวจซ้ำอีกครั้งและคืน error ที่อธิบายสาเหตุ

ยอดสุทธิคิดจากเงินที่จ่ายไป ลบส่วนแบ่งที่ต้องรับผิดชอบ ดังนั้นบิล `100.00` ที่ Alice จ่ายและหารสามคนจะได้ `alice: 66.66`, `bob: -33.33`, `carol: -33.33` ยอดบวกคือเงินที่ต้องได้รับคืน ยอดลบคือเงินที่ต้องจ่ายคืน และรวมทุกคนได้ `0.00`

ฐานข้อมูลรวมเครดิตกับเดบิตใน query เดียวเพื่อให้เห็น snapshot เดียวกันระหว่างที่มีการเพิ่มหรือลบบิล ยอดรวมใช้ความแม่นยำของ `NUMERIC` ต่อไปได้แม้ยอดหลายบิลจะเกินเพดานของบิลเดียว สมาชิกที่ยังไม่มีรายการก็แสดง `0.00` ด้วย

## สิทธิ์ การส่งซ้ำ และการลบบิล

ทุก request ใช้ `X-User` ตามโจทย์เพื่อเลือกผู้ใช้ตัวอย่าง แล้ว backend ตรวจว่าผู้ขอ ผู้จ่าย และผู้ร่วมหารเป็นสมาชิกกลุ่ม ผมเลือกตอบ `404` ทั้งกรณีไม่พบกลุ่มและไม่มีสิทธิ์ เพื่อไม่เปิดเผยว่ากลุ่มที่คนนั้นเข้าถึงไม่ได้มีอยู่จริง ผู้ขอเพิ่มบิลแทนคนอื่นในกลุ่มได้ และผู้จ่ายไม่จำเป็นต้องอยู่ในรายชื่อคนหาร

`POST` ต้องส่ง `Idempotency-Key` มาด้วย คีย์หนึ่งใช้กับการเพิ่มบิลหนึ่งครั้ง ถ้าส่ง request เดิมซ้ำ เช่น เน็ตหลุดแล้วกดลองใหม่ ให้ใช้คีย์เดิม backend จะคืนบิลเดิม (`200`) แทนการสร้างใหม่ (`201`) ถ้าเป็นบิลใหม่ค่อยใช้คีย์ใหม่

ผมกำหนด unique constraint ที่คู่ `group_id` กับ key และใช้ `ON CONFLICT` ของ PostgreSQL รับมือ request ที่เข้ามาพร้อมกัน การบันทึกบิลกับ shares อยู่ใน transaction เดียวกัน การตรวจสิทธิ์เกิดก่อนค้นคีย์เดิม และคีย์เดิมจะคืนข้อมูลที่สร้างไว้ รวมถึงกรณีส่ง body เปลี่ยนแต่ยังผ่านการตรวจรูปแบบ ส่วน JSON ที่เสียหรือโครงสร้างไม่ถูกต้องยังได้ `422`

ฝั่งเว็บสร้างคีย์ด้วย `crypto.randomUUID()` และเก็บ request ที่กำลังส่งใน `sessionStorage` ถ้าไม่ได้รับคำตอบที่ยืนยันผล ระบบให้ลองส่งรายการเดิมและบล็อกการเพิ่มบิลใหม่ไว้ก่อน ระหว่างเพิ่ม ลบ หรือรอยืนยัน ก็เปลี่ยนผู้ใช้หรือกลุ่มไม่ได้ เมื่อสำเร็จจึงล้างฟอร์มและโหลดรายการกับยอดสุทธิจาก API ใหม่ การโหลดข้อมูลล้มเหลวหลังบันทึกจะแสดงแยกจากกรณีบันทึกไม่สำเร็จ และ response เก่าจะไม่เขียนทับข้อมูลของผู้ใช้หรือกลุ่มใหม่

บิลแก้ไขไม่ได้ การลบเป็น soft delete โดยเก็บแถวเดิม shares และ key ไว้ แล้วตั้ง flag ว่าลบแล้ว รายการที่ลบจะไม่อยู่ใน list และไม่นำมาคิดยอดสุทธิ ถ้า replay คีย์เดิมก็ยังคืนบิลที่ลบแล้ว ไม่สร้างบิลกลับมา

ผู้จ่าย (`paid_by`) เป็นคนลบได้ แม้คนที่เพิ่มบิลจะเป็นสมาชิกคนอื่น ผมเลือกให้ลบซ้ำโดยผู้จ่ายได้ `204` เหมือนเดิม ส่วนสมาชิกที่ไม่ใช่ผู้จ่ายได้ `403` แม้บิลถูกลบไปแล้ว ถ้าไม่พบบิลหรือบิลอยู่คนละกลุ่มได้ `404` รูปแบบ response ของ balances เป็น object ชื่อสมาชิกกับจำนวนเงิน และเรียงชื่อสมาชิกตามตัวอักษร รายละเอียดเหล่านี้เป็นข้อเลือกที่บันทึกไว้เมื่อโจทย์ไม่ได้ระบุรูปแบบตายตัว

Error ของ API ใช้ JSON รูปแบบเดียวกัน พร้อม HTTP status ตามเหตุการณ์ Frontend แปลงเป็นข้อความไทย เช่น ยอดส่วนแบ่งไม่ตรงกับบิล หรือผู้จ่ายต้องอยู่ในกลุ่ม โดยเก็บค่าที่กรอกไว้เมื่อแก้ข้อมูลแล้วลองใหม่ได้

## รัน tests และ checks

หลังติดตั้งแล้ว โหลดค่าจาก `.env` ของเครื่องตัวเองเข้า terminal จาก root ก่อน ใช้กับไฟล์ที่เราเตรียมและเชื่อถือเท่านั้น เพราะคำสั่งนี้อ่านไฟล์เป็น shell script

```sh
set -a
. ./.env
set +a
bash scripts/test-backend.sh
```

เมื่อเตรียม environment แล้ว การรัน backend tests ทั้งชุดใช้คำสั่งเดียวคือ `bash scripts/test-backend.sh`

Tests สร้าง schema ชั่วคราวที่ชื่อสุ่มในฐานทดสอบ และลบ schema นั้นเมื่อจบ role จึงต้องมีสิทธิ์สร้างและลบ schema ของตัวเอง ห้ามชี้ URL นี้ไปฐานข้อมูลแอป

ตรวจ Ruff, formatting และ OpenAPI ที่ commit ไว้จาก root ได้ด้วย

```sh
bash scripts/check-backend.sh
```

ถ้าแก้ API และต้องสร้าง OpenAPI ใหม่ ให้รัน

```sh
cd backend
.venv/bin/python -m splitbill.openapi
```

Frontend มี ESLint, TypeScript และ tests ของการคำนวณเงินกับ pending request ส่วน production build ใช้ Webpack เพราะเคยเจอปัญหา worker ของ Turbopack bind พอร์ตไม่ได้ในสภาพแวดล้อมที่พัฒนา รัน checks และ build จาก root ดังนี้

```sh
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
npm start
```

ต้องตั้ง `NEXT_PUBLIC_API_URL` ให้ถูกก่อน build เพราะ Next ฝังค่านี้ลงในไฟล์ frontend ตั้งแต่ตอน build ฟอนต์ Noto Sans Thai อยู่ใน repository พร้อม OFL license จึงไม่ต้องเรียก Google Fonts ตอน build หรือเปิดหน้าเว็บ

### ทดสอบ browser กับ backend จริง

ติดตั้ง Playwright แยกสำหรับงานทดสอบ แล้วรันจาก root คำสั่งนี้เปิด API และ frontend ของตัวเอง ไม่ต้องใช้ development servers ที่เปิดไว้

```sh
backend/.venv/bin/python -m pip install playwright==1.64.1
backend/.venv/bin/python -m playwright install chromium
backend/.venv/bin/python scripts/test-frontend-integration.py
```

Runner อ่าน `TEST_DATABASE_URL` จาก environment หรือ root `.env` ตรวจว่าเป็น PostgreSQL 16 และแยกฐานจากแอป จากนั้นสร้าง schema สุ่ม migrate/seed และ build Next ให้เรียก API ทดสอบที่พอร์ต `8059` แล้วเปิด frontend ที่ `3001` สองพอร์ตนี้ต้องว่าง เปลี่ยนได้ด้วย `--api-port` และ `--web-port` เมื่อจบจะปิด process ของตัวเองและลบ schema ทดสอบ

Tests ของ backend กับ browser รวมกันครอบคลุม equal/exact, precision, สิทธิ์กลุ่ม, idempotency ทั้งคำขอพร้อมกันและกรณีคำตอบหาย, payer-only delete, ยอดรวมศูนย์ และ response เก่าที่กลับมาช้า การจำลองปัญหาใช้การหน่วงหรือทิ้ง response หลัง backend จริงบันทึกแล้ว ไม่ใช้ข้อมูลสำเร็จปลอมมาแทน API หรือ PostgreSQL

ภาพจาก runner อยู่ใน `design-system` ส่วนรอบที่ไม่ผ่านจะทิ้งหลักฐานไว้ใน temporary directory หลังรัน runner ถ้าจะใช้ `npm start` ตามปกติ ให้ build ใหม่ด้วย API URL ปกติก่อน เพราะ build ทดสอบชี้ไปพอร์ต `8059` ส่วน `npm run dev` อ่าน config ปกติแยกอยู่แล้ว

### ผลตรวจที่บันทึกไว้

ที่ commit [`d188cae`](https://github.com/WajanaPiromnok/split-bill/commit/d188cae9a5d0089a7de5322090266aa826d84863) CI ผ่าน [backend 151 tests](https://github.com/WajanaPiromnok/split-bill/actions/runs/41661760076) และ [frontend/full-stack 16 ชุด](https://github.com/WajanaPiromnok/split-bill/actions/runs/41661760324) พร้อม native Node tests 6 เคส, lint, types และ production build ฝั่ง backend ตรวจทั้ง migration/seed และ OpenAPI ด้วย

เคสบังคับทั้งหกตามโจทย์มีอยู่ใน pytest ได้แก่ หาร `100.00` สามคนและยอดรวมศูนย์, exact รวมไม่ตรง, จำนวนเงินสามตำแหน่ง, คีย์ซ้ำไม่สร้างบิลซ้ำ, Alice อ่านหรือเขียนกลุ่ม 2 ไม่ได้ และเฉพาะผู้จ่ายลบบิลได้ มีการทดสอบ concurrent idempotency ด้วย connection PostgreSQL คนละตัว รวมถึง rollback เมื่อเขียนไม่ครบ

Browser checks ตรวจจอ 375, 390, 768, 1024 และ 1440px, keyboard/focus และ reduced motion ผลนี้เป็นหลักฐานของ Chromium ส่วน commit ที่ใหม่กว่านั้นต้องดูผลของ revision นั้นใน [GitHub Actions](https://github.com/WajanaPiromnok/split-bill/actions) อีกครั้ง

## ข้อจำกัดและสิ่งที่จะทำต่อ

`X-User` เป็นการเลือกผู้ใช้ตามโจทย์ ตอนนี้ยังไม่มีระบบสมัครสมาชิกหรือ login จริง และยังไม่ได้เลือก hosting ถ้าจะเปิดให้คนทั่วไปใช้ ผมจะทำ authentication และจัดการ secrets ของแต่ละ environment ก่อน deploy

หน้าเว็บใช้ผู้ใช้และกลุ่มจาก seed จึงยังสร้างกลุ่มหรือเพิ่มสมาชิกจากหน้าเว็บไม่ได้ รายการบิลโหลดทั้งกลุ่ม ถ้าข้อมูลมากขึ้น ขั้นต่อไปคือเพิ่ม pagination แล้วทดสอบสิทธิ์กับการเรียงรายการของแต่ละหน้า ส่วน browser อื่นนอกจาก Chromium ยังต้องตรวจเพิ่ม

Settlement suggestions, repayments และ Docker Compose เป็น optional ตามโจทย์ ยังไม่ได้ทำ รอบนี้เก็บงานไว้ที่ API กับหน้าแบ่งบิลที่ทดสอบแล้วก่อน UI ยังไม่คำนวณว่าใครต้องโอนให้ใคร และไม่มีการรับชำระเงินจริง

Backend แยก routing, business rules และ data access ตามหน้าที่ Frontend ใช้ native form controls, React state และ `fetch` โดยยังไม่เพิ่ม form/state/query library เพราะ flow ตอนนี้จัดการได้ในหน้าเดียว แนวทางที่ตกลงกันและประวัติแต่ละ milestone อยู่ใน [แผน backend](docs/superpowers/plans/2026-11-03-delete-balances.md), [แผน expenses](docs/superpowers/plans/2026-11-02-expenses.md) และ [แผน frontend](docs/frontend-plan.md)

## เวลาที่ใช้และการใช้ AI

เวลารวมประมาณ 12 man-hours ครับ มาจากเวลาที่มีบันทึกไว้สำหรับ baseline ประมาณ 30 ถึง 45 นาที และ frontend/local review ประมาณ 1 ชั่วโมง รวมกับเวลาที่ผมใช้เรียนรู้ เขียน ทดสอบ และแก้ไขเพิ่มอีกประมาณ 10 ชั่วโมง ตัวเลขนี้เป็นประมาณการ ไม่ได้จับเวลาแยกครบทุกกิจกรรม

ผมใช้ Codex และเครื่องมือ AI ช่วยบางส่วน แล้วตรวจ diff กับโจทย์ รัน checks และทดสอบกับฐานข้อมูลจริงก่อนส่งแต่ละ milestone รายละเอียดเครื่องมือ prompt ที่ใช้ ตัวอย่างคำตอบที่ผิด วิธีตรวจเจอ และวิธีแก้อยู่ใน [AI_NOTES.md](AI_NOTES.md)

## Branch และการส่งต่องาน

ใช้สาม branch ตาม [Git workflow](docs/git-workflow.md): `main` เป็นฐานร่วมที่รับ milestone แล้ว, `dev/backend` สำหรับ backend และ `dev/frontend` สำหรับ frontend ประวัติ commit แยกตามงานที่ทำและเก็บ commit ย่อยไว้ผ่าน merge commit เมื่อรวม PR จากนั้นค่อย sync `main` กลับเข้าทั้งสอง dev branches

รอบนี้ผมจะเปิด PR เอง ก่อนส่งต้องระบุ branch/SHA ที่มีทั้ง backend และ frontend และตรวจว่า repository เปิดอ่านได้ตามเงื่อนไขของโจทย์ ถ้าใช้ private repository ต้องให้บัญชี `@alkchowpa` เข้าถึงด้วย การตั้งค่า CI มีแล้ว ส่วน server-enforced branch protection ยังไม่ได้ยืนยันเพราะ GitHub ตอบ `403` ตอนอ่าน rules ของ private repository

ตรวจ revision ที่กำลังจะส่งได้ด้วย

```sh
git rev-parse HEAD
git ls-remote --heads origin main dev/backend dev/frontend
```
