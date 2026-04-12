import streamlit as st
import json
from datetime import datetime, timedelta
import plotly.express as px

# ==========================================
# Cấu hình trang Streamlit
# ==========================================
st.set_page_config(page_title="Dashboard Phân Tích Tưới", page_icon="🌱", layout="wide")

st.title("🌱 Dashboard Phân Tích Giai Đoạn Tưới Nhỏ Giọt")

# ==========================================
# ⚙️ GIAO DIỆN CÀI ĐẶT (SIDEBAR)
# ==========================================
st.sidebar.header("📁 Tải Dữ Liệu Lên")

# 1. Tải nhiều file Tưới & Tạo Checkbox
file_tuoi_uploads = st.sidebar.file_uploader("1. Tải các file Lịch nhỏ giọt (.json)", type=['json'], accept_multiple_files=True)
selected_tuoi_files = []
if file_tuoi_uploads:
    st.sidebar.markdown("**👉 Chọn file Lịch nhỏ giọt cần đọc:**")
    for f in file_tuoi_uploads:
        if st.sidebar.checkbox(f"📄 {f.name}", value=True, key=f"tuoi_{f.name}"):
            selected_tuoi_files.append(f)

# 2. Tải nhiều file Châm phân & Tạo Checkbox
st.sidebar.markdown("<br>", unsafe_allow_html=True)
file_cham_phan_uploads = st.sidebar.file_uploader("2. Tải các file Châm phân (.json)", type=['json'], accept_multiple_files=True)
selected_cp_files = []
if file_cham_phan_uploads:
    st.sidebar.markdown("**👉 Chọn file Châm phân cần đọc:**")
    for f in file_cham_phan_uploads:
        if st.sidebar.checkbox(f"📄 {f.name}", value=True, key=f"cp_{f.name}"):
            selected_cp_files.append(f)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Cấu hình thông số")

STT_CAN_TIM = st.sidebar.text_input("STT Cần Phân Tích", value="4")

st.sidebar.subheader("Ngưỡng phân chia Giai đoạn")
SO_NGAY_ON_DINH = st.sidebar.number_input("⏳ Số ngày ổn định (Chống nhiễu)", value=2, step=1, min_value=1, help="Số ngày liên tiếp có giá trị same same nhau để được công nhận là một Giai đoạn mới.")

SAI_SO_EC_TT = st.sidebar.number_input("1. Sai số EC Thực Tế", value=0.20, step=0.05)
SAI_SO_EC_YC = st.sidebar.number_input("2. Sai số EC Yêu Cầu", value=0.15, step=0.05)
SAI_SO_TONG_PHUT = st.sidebar.number_input("3. Sai số Tổng Thời Gian (Phút)", value=10.0, step=1.0)

st.sidebar.subheader("Ngưỡng lọc dữ liệu")
GIAY_TUOI_TOI_THIEU = st.sidebar.number_input("Giây tưới tối thiểu", value=20)
GIAY_TUOI_TOI_DA = st.sidebar.number_input("Giây tưới tối đa (Lọc lỗi)", value=3600)
SO_NGAY_CHUYEN_VU = 2.0
SO_NGAY_TOI_THIEU = 7

# ==========================================
# 🧠 HÀM XỬ LÝ DỮ LIỆU CỐT LÕI
# ==========================================
def lay_ec_yeu_cau_tai_thoi_diem(tg_tuoi, lich_su_ec):
    ec_hien_tai = 0.0
    for record in lich_su_ec:
        if record['Thoi_gian'] <= tg_tuoi:
            ec_hien_tai = record['EC_YC']
        else:
            break
    return ec_hien_tai

def phan_tich_giai_doan_array(danh_sach_ngay, values, sai_so, so_ngay_on_dinh):
    stages = {}
    gd_current = 1
    goc_val = None
    buffer = []
    
    for i, ngay in enumerate(danh_sach_ngay):
        val = values[i]
        
        if goc_val is None:
            goc_val = val
            stages[ngay] = gd_current
            continue
            
        if abs(val - goc_val) >= sai_so:
            buffer.append({'ngay': ngay, 'val': val})
            
            if len(buffer) >= so_ngay_on_dinh:
                buf_vals = [x['val'] for x in buffer]
                if max(buf_vals) - min(buf_vals) <= sai_so:
                    gd_current += 1
                    goc_val = sum(buf_vals) / len(buf_vals) 
                    for item in buffer:
                        stages[item['ngay']] = gd_current
                    buffer = []
                else:
                    oldest = buffer.pop(0)
                    stages[oldest['ngay']] = gd_current
        else:
            for item in buffer:
                stages[item['ngay']] = gd_current
            buffer = []
            stages[ngay] = gd_current
            
    for item in buffer:
        stages[item['ngay']] = gd_current
        
    return stages

@st.cache_data
def process_data(stt, so_ngay_on_dinh, ss_ec_tt, ss_ec_yc, ss_tong_phut, giay_min, giay_max, data_tuoi, data_cp):
    try:
        lich_su_ec_yc = []
        for item in data_cp:
            if str(item.get('STT')) == stt and item.get('Thời gian') and 'EC yêu cầu' in item:
                try:
                    tg = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    ec_val = float(item.get('EC yêu cầu', 0)) / 100.0
                    lich_su_ec_yc.append({'Thoi_gian': tg, 'EC_YC': ec_val})
                except ValueError: pass
        lich_su_ec_yc.sort(key=lambda x: x['Thoi_gian'])

        du_lieu_da_loc = []
        for item in data_tuoi:
            if str(item.get('STT')) == stt and item.get('Thời gian'):
                tg_hien_tai = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                du_lieu_da_loc.append({
                    'Thời gian': tg_hien_tai,
                    'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                    'EC_Yeu_Cau': lay_ec_yeu_cau_tai_thoi_diem(tg_hien_tai, lich_su_ec_yc),
                    'EC_Thuc_Te': float(item.get('TBEC', 0)) / 100.0,
                    'pH': float(item.get('TBPH', 0)) / 100.0
                })

        if not du_lieu_da_loc: return None, f"❌ Không có dữ liệu cho STT {stt}."
        du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

        danh_sach_mua_vu = []
        mua_hien_tai = [du_lieu_da_loc[0]]
        for i in range(1, len(du_lieu_da_loc)):
            if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                danh_sach_mua_vu.append(mua_hien_tai)
                mua_hien_tai = []
            mua_hien_tai.append(du_lieu_da_loc[i])
        if mua_hien_tai: danh_sach_mua_vu.append(mua_hien_tai)

        ket_qua_bao_cao = []
        for mua_vu in danh_sach_mua_vu:
            ngay_bat_dau = mua_vu[0]['Thời gian']
            ngay_ket_thuc = mua_vu[-1]['Thời gian']
            if (ngay_ket_thuc - ngay_bat_dau).days < SO_NGAY_TOI_THIEU: continue

            cac_cu_tuoi = []; tg_bat = None; tong_lan = 0
            for dong in mua_vu:
                if dong['Trạng thái'] == 'Bật': tg_bat = dong['Thời gian']
                elif dong['Trạng thái'] == 'Tắt' and tg_bat is not None:
                    giay_chay = (dong['Thời gian'] - tg_bat).total_seconds()
                    if giay_min <= giay_chay <= giay_max:
                        cac_cu_tuoi.append({
                            'Ngày': tg_bat.date(), 'Giây chạy': giay_chay,
                            'EC_Yeu_Cau': dong['EC_Yeu_Cau'], 'EC_Thuc_Te': dong['EC_Thuc_Te'], 'pH': dong['pH']
                        })
                        tong_lan += 1
                    tg_bat = None

            thong_ke = {}
            for cu in cac_cu_tuoi:
                ng = cu['Ngày']
                if ng not in thong_ke: thong_ke[ng] = {'So_lan': 0, 'Tong_giay': 0, 'Tong_EC_YC': 0, 'Tong_EC_TT': 0, 'Tong_pH': 0}
                thong_ke[ng]['So_lan'] += 1
                thong_ke[ng]['Tong_giay'] += cu['Giây chạy']
                thong_ke[ng]['Tong_EC_YC'] += cu['EC_Yeu_Cau']
                thong_ke[ng]['Tong_EC_TT'] += cu['EC_Thuc_Te']
                thong_ke[ng]['Tong_pH'] += cu['pH']

            danh_sach_ngay = sorted(thong_ke.keys())
            
            ec_tt_vals = [thong_ke[n]['Tong_EC_TT'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            ec_yc_vals = [thong_ke[n]['Tong_EC_YC'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            tong_phut_vals = [thong_ke[n]['Tong_giay'] / 60 for n in danh_sach_ngay]
            
            stages_ec_tt = phan_tich_giai_doan_array(danh_sach_ngay, ec_tt_vals, ss_ec_tt, so_ngay_on_dinh)
            stages_ec_yc = phan_tich_giai_doan_array(danh_sach_ngay, ec_yc_vals, ss_ec_yc, so_ngay_on_dinh)
            stages_tuoi = phan_tich_giai_doan_array(danh_sach_ngay, tong_phut_vals, ss_tong_phut, so_ngay_on_dinh)

            bang_bao_cao_ngay = []
            for i, ngay in enumerate(danh_sach_ngay):
                bang_bao_cao_ngay.append({
                    "Ngày_Str": ngay.strftime("%d/%m/%Y"),
                    "GĐ_EC_Thực": f"GĐ {stages_ec_tt[ngay]}",
                    "GĐ_EC_YC": f"GĐ {stages_ec_yc[ngay]}",
                    "GĐ_Tưới": f"GĐ {stages_tuoi[ngay]}",
                    "Số_Lần": thong_ke[ngay]['So_lan'],
                    "Tổng_TG_Phút": round(tong_phut_vals[i], 2),
                    "EC_Yêu_Cầu": round(ec_yc_vals[i], 2),
                    "EC_Thực_Tế": round(ec_tt_vals[i], 2),
                    "pH_TB": round(thong_ke[ngay]['Tong_pH'] / thong_ke[ngay]['So_lan'], 2)
                })

            ket_qua_bao_cao.append({"ngay_bat_dau": ngay_bat_dau, "ngay_ket_thuc": ngay_ket_thuc, "tong_lan_tuoi": tong_lan, "data": bang_bao_cao_ngay})
            
        return ket_qua_bao_cao, "Thành công"
    except Exception as e: return None, f"❌ Lỗi xử lý dữ liệu: {e}"

# ==========================================
# 📊 QUẢN LÝ LUỒNG CHẠY & HIỂN THỊ
# ==========================================
if not selected_tuoi_files or not selected_cp_files:
    st.info("👈 Vui lòng tải lên và TÍCH CHỌN ít nhất 1 file Lịch nhỏ giọt và 1 file Châm phân ở thanh bên trái để bắt đầu.")
else:
    try:
        raw_data_tuoi = []
        raw_data_cp = []
        
        # Gộp tất cả dữ liệu từ các file Lịch nhỏ giọt ĐƯỢC TÍCH
        for f in selected_tuoi_files:
            f.seek(0)
            data = json.load(f)
            if isinstance(data, list):
                raw_data_tuoi.extend(data)
            else:
                raw_data_tuoi.append(data)
                
        # Gộp tất cả dữ liệu từ các file Châm phân ĐƯỢC TÍCH
        for f in selected_cp_files:
            f.seek(0)
            data = json.load(f)
            if isinstance(data, list):
                raw_data_cp.extend(data)
            else:
                raw_data_cp.append(data)
        
        with st.spinner('Đang gộp file và phân tích dữ liệu...'):
            ket_qua, thong_bao = process_data(
                STT_CAN_TIM, SO_NGAY_ON_DINH, SAI_SO_EC_TT, SAI_SO_EC_YC, SAI_SO_TONG_PHUT, 
                GIAY_TUOI_TOI_THIEU, GIAY_TUOI_TOI_DA, raw_data_tuoi, raw_data_cp 
            )

        if ket_qua is None:
            st.error(thong_bao)
        else:
            st.success(f"Đã gộp {len(selected_tuoi_files)} file Tưới & {len(selected_cp_files)} file Châm phân. Phân tích hoàn tất cho STT = {STT_CAN_TIM}!")
            
            for idx, mua_vu in enumerate(ket_qua):
                st.markdown(f"### 🌿 MÙA VỤ SỐ {idx + 1}")
                
                # Tính toán ngày gốc của toàn mùa vụ
                ngay_bat_dau_goc = mua_vu['ngay_bat_dau'].date()
                ngay_ket_thuc_goc = mua_vu['ngay_ket_thuc'].date()
                so_ngay_mua_vu = (ngay_ket_thuc_goc - ngay_bat_dau_goc).days + 1
                
                st.caption(f"🗓️ Dữ liệu gốc: Từ **{ngay_bat_dau_goc.strftime('%d/%m/%Y')}** đến **{ngay_ket_thuc_goc.strftime('%d/%m/%Y')}** ({so_ngay_mua_vu} ngày) | 💧 Tổng cữ tưới: **{mua_vu['tong_lan_tuoi']}** lần")
                
                # --- CHỨC NĂNG LỌC BẰNG 2 Ô TỪ NGÀY / ĐẾN NGÀY RIÊNG BIỆT ---
                st.markdown("**📅 Chọn khoảng thời gian để phân tích:**")
                col_d1, col_d2, col_d3 = st.columns([1, 1, 2]) # Tạo 3 cột, để 2 cột đầu ngắn, cột cuối rỗng cho đẹp
                with col_d1:
                    start_date = st.date_input(
                        "Từ ngày:",
                        value=ngay_bat_dau_goc,
                        min_value=ngay_bat_dau_goc,
                        max_value=ngay_ket_thuc_goc,
                        key=f"start_date_{idx}"
                    )
                with col_d2:
                    end_date = st.date_input(
                        "Đến ngày:",
                        value=ngay_ket_thuc_goc,
                        min_value=start_date, # Bắt buộc Đến ngày phải lớn hơn hoặc bằng Từ ngày
                        max_value=ngay_ket_thuc_goc,
                        key=f"end_date_{idx}"
                    )
                
                # Lọc dữ liệu dựa trên khoảng thời gian
                data_mua_vu = []
                for row in mua_vu['data']:
                    row_date = datetime.strptime(row["Ngày_Str"], "%d/%m/%Y").date()
                    if start_date <= row_date <= end_date:
                        data_mua_vu.append(row)
                
                # Nếu không có dữ liệu trong khoảng thời gian đã chọn
                if not data_mua_vu:
                    st.warning("⚠️ Không có dữ liệu trong khoảng thời gian bạn đã chọn.")
                    st.divider()
                    continue
                # -------------------------------------------
                
                tieuchi_mapping = {
                    "🎯 EC Yêu Cầu (Trung bình)": {"cot_gia_tri": "EC_Yêu_Cầu", "cot_giai_doan": "GĐ_EC_YC"},
                    "🧪 EC Thực Tế (Trung bình)": {"cot_gia_tri": "EC_Thực_Tế", "cot_giai_doan": "GĐ_EC_Thực"},
                    "⏱️ Tổng Thời Gian Tưới / Ngày (Phút)": {"cot_gia_tri": "Tổng_TG_Phút", "cot_giai_doan": "GĐ_Tưới"}
                }
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown("<br>", unsafe_allow_html=True)
                    tieuchi_chon = st.selectbox(f"📊 Chọn tiêu chí biểu đồ:", list(tieuchi_mapping.keys()), key=f"selectbox_{idx}")
                
                cot_du_lieu = tieuchi_mapping[tieuchi_chon]["cot_gia_tri"]
                cot_giai_doan = tieuchi_mapping[tieuchi_chon]["cot_giai_doan"]
                
                max_y = max([row[cot_du_lieu] for row in data_mua_vu]) * 1.2 if data_mua_vu else 1

                fig = px.bar(
                    data_mua_vu, x="Ngày_Str", y=cot_du_lieu, color=cot_giai_doan, text=cot_du_lieu,
                    title=f"Biểu đồ {tieuchi_chon.split('(')[0].strip()}",
                    labels={"Ngày_Str": "Ngày", cot_du_lieu: "Giá trị", cot_giai_doan: "Giai đoạn"},
                    color_discrete_sequence=px.colors.qualitative.Plotly 
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, max_y])) 
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.markdown(f"#### 🔍 Chi Tiết Theo {cot_giai_doan.replace('_', ' ')}")
                
                danh_sach_gd = list(set([row[cot_giai_doan] for row in data_mua_vu]))
                danh_sach_gd.sort(key=lambda x: int(x.replace('GĐ ', ''))) 
                danh_sach_chon = ["Tất cả các Giai đoạn"] + danh_sach_gd
                
                gd_chon = st.selectbox(
                    "👉 Chọn Giai đoạn để xem chi tiết:", 
                    danh_sach_chon, 
                    key=f"select_gd_{idx}"
                )
                
                if gd_chon == "Tất cả các Giai đoạn":
                    data_filtered = data_mua_vu
                else:
                    data_filtered = [row for row in data_mua_vu if row[cot_giai_doan] == gd_chon]
                    
                    if data_filtered:
                        st.info(f"**📊 Thống kê tóm tắt cho {gd_chon}:**")
                        col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns([2, 1, 1.2, 1.2, 1.2, 1])
                        
                        ngay_dau = data_filtered[0]['Ngày_Str']
                        ngay_cuoi = data_filtered[-1]['Ngày_Str']
                        so_ngay = len(data_filtered)
                        
                        tb_ec_yc = sum(row['EC_Yêu_Cầu'] for row in data_filtered) / so_ngay
                        tb_ec_tt = sum(row['EC_Thực_Tế'] for row in data_filtered) / so_ngay
                        tb_tg = sum(row['Tổng_TG_Phút'] for row in data_filtered) / so_ngay
                        tb_ph = sum(row['pH_TB'] for row in data_filtered) / so_ngay
                        
                        col_m1.metric("Thời gian", f"{ngay_dau} - {ngay_cuoi}")
                        col_m2.metric("Kéo dài", f"{so_ngay} ngày")
                        col_m3.metric("EC Yêu Cầu (TB)", f"{round(tb_ec_yc, 2)}")
                        col_m4.metric("EC Thực Tế (TB)", f"{round(tb_ec_tt, 2)}")
                        col_m5.metric("TG Tưới (TB)", f"{round(tb_tg, 2)} phút")
                        col_m6.metric("pH (TB)", f"{round(tb_ph, 2)}")
                        st.markdown("<br>", unsafe_allow_html=True)

                st.markdown("#### 📋 Bảng Dữ Liệu")
                
                data_display = []
                for row in data_filtered:
                    data_display.append({
                        "📅 Ngày": row["Ngày_Str"],
                        "🏷️ GĐ(EC.Thực)": row["GĐ_EC_Thực"],
                        "🏷️ GĐ(EC.YC)": row["GĐ_EC_YC"],
                        "🏷️ GĐ(Tưới)": row["GĐ_Tưới"],
                        "💧 Số Lần": row["Số_Lần"],
                        "⏱️ Tổng TG (Ph)": row["Tổng_TG_Phút"],
                        "🎯 EC Y.Cầu": row["EC_Yêu_Cầu"],
                        "🧪 EC T.Tế": row["EC_Thực_Tế"],
                        "⚗️ pH TB": row["pH_TB"]
                    })
                
                st.dataframe(data_display, use_container_width=True)
                st.divider()

    except json.JSONDecodeError:
        st.error("❌ Lỗi định dạng file! Vui lòng đảm bảo bạn đã tải lên đúng file .json hợp lệ.")
