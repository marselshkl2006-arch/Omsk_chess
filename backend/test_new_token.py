import requests
import json

token = "lip_GcWsQv9qFJZ9Vhuiplml"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Проверка аккаунта
print("📡 Проверка аккаунта...")
response = requests.get("https://lichess.org/api/account", headers=headers)
if response.status_code == 200:
    data = response.json()
    print(f"✅ Аккаунт: {data.get('username')}")
else:
    print(f"❌ Ошибка: {response.status_code}")
    exit()

# Проверка прав
print("\n📡 Проверка прав...")
response = requests.get("https://lichess.org/api/token", headers=headers)
if response.status_code == 200:
    scopes = response.json().get("scopes", [])
    print(f"✅ Права: {scopes}")
else:
    print(f"❌ Ошибка: {response.status_code}")

# Пробуем создать трансляцию
print("\n📡 Создание трансляции...")
url = "https://lichess.org/api/broadcast/new"
data = {
    "name": "Тестовая трансляция Омской области",
    "description": "#ОмскШахматнаяСтолица\n\nТестовая трансляция",
    "markdown": True
}

response = requests.post(url, headers=headers, json=data)
print(f"Статус: {response.status_code}")
if response.status_code == 200:
    print("✅ Успех!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"❌ Ошибка: {response.text[:500]}")
