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
file_tuoi_uploads = st.sidebar.file_uploader("1. Tải file Lịch nhỏ giọt (.json)", type=['json'], accept_multiple_files=True)
selected_tuoi_files = []
if file_tuoi_uploads:
    st.sidebar.markdown("**👉 Chọn file Lịch nhỏ giọt:**")
    for f in file_tuoi_uploads:
        if st.sidebar.checkbox(f"📄 {f.name}", value=True, key=f"tuoi_{f.name}"):
            selected_tuoi_files.append(f)

# 2. Tải nhiều file Châm phân & Tạo Checkbox
st.sidebar.markdown("<br>", unsafe_allow_html=True)
file_cham_phan_uploads = st.sidebar.file_uploader("2. Tải file Châm phân (.json)", type=['json'], accept_multiple_files=True)
selected_cp_files = []
if file_cham_phan_uploads:
    st.sidebar.markdown("**👉 Chọn file Châm phân:**")
    for f in file_cham_phan_uploads:
        if st.sidebar.checkbox(f"📄 {f.name}", value=True, key=f"cp_{f.name}"):
            selected_cp_files.append(f)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Cấu hình thông số")

STT_CAN_TIM = st.sidebar.text_input("STT Cần Phân Tích", value="4")

st.sidebar.subheader("Cắt Mùa Vụ")
TIEU_CHI_MUA_VU = st.sidebar.radio("Tiêu chí xác định Mùa vụ mới:", ["⏳ Theo thời gian nghỉ tưới", "🧪 Theo sự sụt giảm EC"])
SO_NGAY_CHUYEN_VU = st.sidebar.number_input("Số ngày nghỉ tối thiểu (Nếu chọn Thời gian)", value=2.0)
EC_NGUONG_CHUYEN_VU = st.sidebar.number_input("Ngưỡng EC chuyển vụ (Nếu chọn EC)", value=0.5, step=0.1, help="Khi EC Yêu cầu tụt xuống dưới mức này, hệ thống sẽ hiểu là đang dọn vườn/rửa giá thể.")

st.sidebar.subheader("Ngưỡng phân chia Giai đoạn")
SO_NGAY_ON_DINH = st.sidebar.number_input("⏳ Số ngày ổn định (Chống nhiễu)", value=2, step=1, min_value=1)
SAI_SO_EC_TT = st.sidebar.number_input("1. Sai số EC Thực Tế", value=0.20, step=0.05)
SAI_SO_EC_YC = st.sidebar.number_input("2. Sai số EC Yêu Cầu", value=0.15, step=0.05)
SAI_SO_TONG_PHUT = st.sidebar.number_input("3. Sai số Tổng Thời Gian (Phút)", value=10.0, step=1.0)

st.sidebar.subheader("Ngưỡng lọc dữ liệu")
GIAY_TUOI_TOI_THIEU = st.sidebar.number_input("Giây tưới tối thiểu", value=20)
GIAY_TUOI_TOI_DA = st.sidebar.number_input("Giây tưới tối đa (Lọc lỗi)", value=3600)
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
def process_data(stt, so_ngay_on_dinh, ss_ec_tt, ss_ec_yc, ss_tong_phut, giay_min, giay_max, tieu_chi_mua_vu, so_ngay_chuyen_vu, ec_nguong_chuyen_vu, data_tuoi, data_cp):
    try:
        # 1. Trích xuất dữ liệu châm phân
        lich_su_ec_yc = []
        for item in data_cp:
            if str(item.get('STT')) == stt and item.get('Thời gian') and 'EC yêu cầu' in item:
                try:
                    tg = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    ec_val = float(item.get('EC yêu cầu', 0)) / 100.0
                    lich_su_ec_yc.append({'Thoi_gian': tg, 'EC_YC': ec_val})
                except ValueError: pass
        lich_su_ec_yc.sort(key=lambda x: x['Thoi_gian'])

        # 2. Lọc dữ liệu tưới và gán EC Yêu cầu
        du_lieu_da_loc = []
        for item in data_tuoi:
            if str(item.get('STT')) == stt and item.get('Thời gian'):
                try:
                    tg_hien_tai = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    
                    # CẬP NHẬT: Xử lý an toàn cho TBEC (chống lỗi khi chuỗi rỗng "")
                    raw_tbec = str(item.get('TBEC', '0')).strip()
                    tbec_val = float(raw_tbec) / 100.0 if raw_tbec else 0.0

                    du_lieu_da_loc.append({
                        'Thời gian': tg_hien_tai,
                        'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                        'EC_Yeu_Cau': lay_ec_yeu_cau_tai_thoi_diem(tg_hien_tai, lich_su_ec_yc),
                        'EC_Thuc_Te': tbec_val
                    })
                except ValueError: pass

        if not du_lieu_da_loc: return None, f"❌ Không có dữ liệu hợp lệ cho STT {stt}."
        du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

        # 3. Phân cắt Mùa vụ theo tiêu chí được chọn
        danh_sach_mua_vu = []
        mua_hien_tai = [du_lieu_da_loc[0]]
        dang_nghi_vu = (du_lieu_da_loc[0]['EC_Yeu_Cau'] <= ec_nguong_chuyen_vu)

        for i in range(1, len(du_lieu_da_loc)):
            dong = du_lieu_da_loc[i]
            dong_truoc = du_lieu_da_loc[i-1]
            cat_vu = False

            if tieu_chi_mua_vu == "⏳ Theo thời gian nghỉ tưới":
                if (dong['Thời gian'] - dong_truoc['Thời gian']) > timedelta(days=so_ngay_chuyen_vu):
                    cat_vu = True
            else: # Theo sụt giảm EC
                if dong['EC_Yeu_Cau'] <= ec_nguong_chuyen_vu:
                    dang_nghi_vu = True
                else:
                    if dang_nghi_vu: 
                        cat_vu = True # Vừa vượt ngưỡng trở lại -> Vụ mới
                        dang_nghi_vu = False
            
            if cat_vu:
                if mua_hien_tai: danh_sach_mua_vu.append(mua_hien_tai)
                mua_hien_tai = []
            
            mua_hien_tai.append(dong)
            
        if mua_hien_tai: danh_sach_mua_vu.append(mua_hien_tai)

        # 4. Gom nhóm theo ngày và tính toán giai đoạn
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
                            'EC_Yeu_Cau': dong['EC_Yeu_Cau'], 'EC_Thuc_Te': dong['EC_Thuc_Te']
                        })
                        tong_lan += 1
                    tg_bat = None

            thong_ke = {}
            for cu in cac_cu_tuoi:
                ng = cu['Ngày']
                if ng not in thong_ke: thong_ke[ng] = {'So_lan': 0, 'Tong_giay': 0, 'Tong_EC_YC': 0, 'Tong_EC_TT': 0}
                thong_ke[ng]['So_lan'] += 1
                thong_ke[ng]['Tong_giay'] += cu['Giây chạy']
                thong_ke[ng]['Tong_EC_YC'] += cu['EC_Yeu_Cau']
                thong_ke[ng]['Tong_EC_TT'] += cu['EC_Thuc_Te']

            if not thong_ke: continue

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
                    "EC_Thực_Tế": round(ec_tt_vals[i], 2)
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
        
        for f in selected_tuoi_files:
            f.seek(0)
            data = json.load(f)
            if isinstance(data, list): raw_data_tuoi.extend(data)
            else: raw_data_tuoi.append(data)
                
        for f in selected_cp_files:
            f.seek(0)
            data = json.load(f)
            if isinstance(data, list): raw_data_cp.extend(data)
            else: raw_data_cp.append(data)
        
        with st.spinner('Đang gộp file và phân tích dữ liệu...'):
            ket_qua, thong_bao = process_data(
                STT_CAN_TIM, SO_NGAY_ON_DINH, SAI_SO_EC_TT, SAI_SO_EC_YC, SAI_SO_TONG_PHUT, 
                GIAY_TUOI_TOI_THIEU, GIAY_TUOI_TOI_DA, TIEU_CHI_MUA_VU, SO_NGAY_CHUYEN_VU, EC_NGUONG_CHUYEN_VU, raw_data_tuoi, raw_data_cp 
            )

        if ket_qua is None:
            st.error(thong_bao)
        elif len(ket_qua) == 0:
            st.warning("⚠️ Không tìm thấy mùa vụ nào đủ số ngày tối thiểu để phân tích. Hãy kiểm tra lại khoảng thời gian của dữ liệu hoặc điều kiện cắt mùa vụ.")
        else:
            st.success(f"Đã xử lý xong! Cắt mùa vụ theo: {TIEU_CHI_MUA_VU}")
            
            for idx, mua_vu in enumerate(ket_qua):
                st.markdown(f"### 🌿 MÙA VỤ SỐ {idx + 1}")
                so_ngay_mua_vu = (mua_vu['ngay_ket_thuc'] - mua_vu['ngay_bat_dau']).days + 1
                st.caption(f"🗓️ Từ **{mua_vu['ngay_bat_dau'].strftime('%d/%m/%Y')}** đến **{mua_vu['ngay_ket_thuc'].strftime('%d/%m/%Y')}** ({so_ngay_mua_vu} ngày) | 💧 Cữ tưới: **{mua_vu['tong_lan_tuoi']}** lần")
                
                data_mua_vu = mua_vu['data'] 
                
                # --- TÍNH TOÁN % TƯƠNG THÍCH THIẾT BỊ ---
                tong_tuong_thich = 0
                count_days = 0
                for row in data_mua_vu:
                    if row['EC_Yêu_Cầu'] > 0:
                        sai_lech = abs(row['EC_Thực_Tế'] - row['EC_Yêu_Cầu']) / row['EC_Yêu_Cầu']
                        ty_le = max(0, 100 - sai_lech * 100)
                        tong_tuong_thich += ty_le
                        count_days += 1
                
                avg_tuong_thich = (tong_tuong_thich / count_days) if count_days > 0 else 0
                
                # --- KHUNG KẾT LUẬN AI ---
                with st.expander(f"💡 ĐÁNH GIÁ VẬN HÀNH (Bấm để xem kết luận)", expanded=True):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("Tương thích EC Thiết bị", f"{round(avg_tuong_thich, 1)}%")
                    
                    with col_b:
                        if avg_tuong_thich >= 90:
                            st.success("**🟢 VẬN HÀNH TỐI ƯU:** Hệ thống châm phân đáp ứng cực kỳ chính xác lệnh của kỹ sư. Mùa vụ duy trì ổn định.")
                        elif avg_tuong_thich >= 80:
                            st.warning("**🟡 CẢNH BÁO NHẸ:** Hệ thống có độ lệch nhẹ giữa Yêu cầu và Thực tế. Cần theo dõi thêm áp lực bơm định lượng.")
                        else:
                            st.error("**🔴 RỦI RO HỆ THỐNG:** Sai lệch quá lớn (>20%). Cây có thể đang bị thiếu hụt dinh dưỡng. Cần kiểm tra rò rỉ phân, e khí bơm hoặc bẩn cảm biến ngay lập tức.")
                
                # --- BIỂU ĐỒ ---
                tieuchi_mapping = {
                    "🎯 EC Yêu Cầu (Trung bình)": {"cot_gia_tri": "EC_Yêu_Cầu", "cot_giai_doan": "GĐ_EC_YC"},
                    "🧪 EC Thực Tế (Trung bình)": {"cot_gia_tri": "EC_Thực_Tế", "cot_giai_doan": "GĐ_EC_Thực"},
                    "⏱️ Tổng Thời Gian Tưới / Ngày (Phút)": {"cot_gia_tri": "Tổng_TG_Phút", "cot_giai_doan": "GĐ_Tưới"}
                }
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    tieuchi_chon = st.selectbox(f"📊 Chọn tiêu chí biểu đồ (Vụ {idx + 1}):", list(tieuchi_mapping.keys()), key=f"selectbox_{idx}")
                
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
                
                # --- CHI TIẾT GIAI ĐOẠN ---
                st.markdown(f"#### 🔍 Chi Tiết Bảng Dữ Liệu")
                
                danh_sach_gd = list(set([row[cot_giai_doan] for row in data_mua_vu]))
                danh_sach_gd.sort(key=lambda x: int(x.replace('GĐ ', ''))) 
                danh_sach_chon = ["Tất cả các Giai đoạn"] + danh_sach_gd
                
                gd_chon = st.selectbox("👉 Chọn Giai đoạn lọc Dataframe:", danh_sach_chon, key=f"select_gd_{idx}")
                
                if gd_chon == "Tất cả các Giai đoạn":
                    data_filtered = data_mua_vu
                else:
                    data_filtered = [row for row in data_mua_vu if row[cot_giai_doan] == gd_chon]
                    if data_filtered:
                        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                        so_ngay = len(data_filtered)
                        tb_ec_yc = sum(row['EC_Yêu_Cầu'] for row in data_filtered) / so_ngay
                        tb_ec_tt = sum(row['EC_Thực_Tế'] for row in data_filtered) / so_ngay
                        tb_tg = sum(row['Tổng_TG_Phút'] for row in data_filtered) / so_ngay
                        
                        col_m1.metric("Thời gian", f"{data_filtered[0]['Ngày_Str']}")
                        col_m2.metric("Kéo dài", f"{so_ngay} ngày")
                        col_m3.metric("EC Yêu Cầu (TB)", f"{round(tb_ec_yc, 2)}")
                        col_m4.metric("EC Thực Tế (TB)", f"{round(tb_ec_tt, 2)}")
                        col_m5.metric("TG Tưới (TB)", f"{round(tb_tg, 2)} phút")
                        st.markdown("<br>", unsafe_allow_html=True)

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
                        "🧪 EC T.Tế": row["EC_Thực_Tế"]
                    })
                
                st.dataframe(data_display, use_container_width=True)
                st.divider()

    except json.JSONDecodeError:
        st.error("❌ Lỗi định dạng file! Vui lòng đảm bảo bạn đã tải lên đúng file .json hợp lệ.")
