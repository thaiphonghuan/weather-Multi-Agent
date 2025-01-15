import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import streamlit as st
from groq import Groq

# Kết nối Google Sheets
def connect_to_google_sheets(sheet_name, credentials_file):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1  # Lấy sheet đầu tiên
    return sheet

# Lấy thông tin thời tiết từ OpenWeatherMap API
def fetch_weather_data(city_name, api_key):
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,  # Thành phố từ người dùng nhập
        "appid": api_key,
        "units": "metric"  # Đơn vị nhiệt độ (Celsius)
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        weather = {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "weather": data["weather"][0]["description"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return weather
    else:
        raise Exception(f"Failed to fetch weather data: {response.status_code} - {response.text}")

# Ghi thông tin thời tiết vào Google Sheets
def save_weather_to_sheet(sheet, weather_data):
    headers = ["Timestamp", "City", "Weather", "Temperature"]
    # Kiểm tra xem Google Sheet có headers chưa
    if not sheet.cell(1, 1).value:
        sheet.append_row(headers)
    # Ghi dữ liệu vào hàng mới
    row = [
        weather_data["timestamp"],
        weather_data["city"],
        weather_data["weather"],
        weather_data["temperature"],
    ]
    sheet.append_row(row)

# Lấy dữ liệu thời tiết cho thành phố cụ thể từ Google Sheet
def fetch_weather_for_city(sheet, city_name):
    records = sheet.get_all_records()  # Lấy tất cả dữ liệu dưới dạng list các dict
    for record in records:
        if record["City"].lower() == city_name.lower():
            temp = str(record["Temperature"])  # Đọc giá trị
            if "." not in temp:  # Thêm dấu chấm nếu thiếu
                temp = temp[:-2] + "." + temp[-2:]
            try:
                record["Temperature"] = float(temp)
            except ValueError:
                raise ValueError(f"Invalid temperature value: {record['Temperature']}")
            return record
    return None

# Tạo prompt từ dữ liệu thời tiết
def create_weather_prompt(weather_data):
    if weather_data:
        city = weather_data.get("City", "Unknown city")
        weather = weather_data.get("Weather", "Unknown weather")
        temperature = weather_data.get("Temperature", "Unknown temperature")
        prompt = f"The current weather in {city} is {weather} with a temperature of {temperature}°C. Can you provide more details about this weather?"
        return prompt
    return None

# Gọi API LLaMA3 để generate câu trả lời
def call_llama3_api(prompt):
    try:
        client = Groq(api_key="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")
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )

        response_text = ""
        for chunk in completion:
            if hasattr(chunk, 'choices') and chunk.choices:
                response_text += chunk.choices[0].delta.content or ""
        return response_text

    except Exception as e:
        return f"Error calling LLaMA3 API: {e}"

# Streamlit Web App

def main():
    st.title("Cooperative Agent - Weather Information Realtime")

    # Nhập tên thành phố
    city_name = st.text_input("Enter the city name:")
    
    if city_name:
        # Lấy thông tin thời tiết
        API_KEY = "d39dad4c0710ba5d064c5cd54ca454a7"  # Thay bằng API key của bạn
        weather_data = fetch_weather_data(city_name, API_KEY)
        
        # Hiển thị thông tin thời tiết
        st.write(f"Weather data for {weather_data['city']}:")
        st.write(f"Temperature: {weather_data['temperature']}°C")
        st.write(f"Weather: {weather_data['weather']}")
        
        # Lưu thông tin vào Google Sheets
        try:
            sheet = connect_to_google_sheets("weather", "C:/Users/Admin/Documents/agent/thinking-banner-447704-f8-9fbd2c30ea0e.json")
            save_weather_to_sheet(sheet, weather_data)
            st.success("Some information about the weather that you maybe need!")
        except Exception as e:
            st.error(f"Error saving data to Google Sheets: {e}")

        # Lấy dữ liệu từ Google Sheets và gọi LLaMA3
        try:
            sheet = connect_to_google_sheets("weather", "C:/Users/Admin/Documents/agent/thinking-banner-447704-f8-9fbd2c30ea0e.json")
            weather_data_from_sheet = fetch_weather_for_city(sheet, city_name)

            if weather_data_from_sheet:
                # Tạo prompt và gọi API LLaMA3
                prompt = create_weather_prompt(weather_data_from_sheet)
                response = call_llama3_api(prompt)
                st.write(f"{response}")
            else:
                st.error("No weather data found for the city.")
        except Exception as e:
            st.error(f"Error processing data: {e}")

if __name__ == "__main__":
    main()
