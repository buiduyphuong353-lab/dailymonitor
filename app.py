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
    # ---------------------------------------------------------
    # [NOTE QUAN TRỌNG]: THUẬT TOÁN ĐÁNH DẤU GIAI ĐOẠN (1, 2, 3...)
    # ---------------------------------------------------------
    # Hàm này nhận vào mảng giá trị (vd: EC 1.2, 1.2, 1.5, 1.5)
    # Nếu giá trị mới lệch so với giá trị cũ vượt mức 'sai_so', 
    # và kéo dài đủ 'so_ngay_on_dinh' thì nó tăng gd_current lên 1 (Giai đoạn mới)
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
                    gd_current += 1  # <--- CHUYỂN GIAI ĐOẠN TẠI ĐÂY
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
        # Lấy lịch sử châm phân
        lich_su_ec_yc = []
        for item in data_cp:
            if str(item.get('STT')) == stt and item.get('Thời gian') and 'EC yêu cầu' in item:
                try:
                    tg = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    ec_val = float(item.get('EC yêu cầu', 0)) / 100.0
                    lich_su_ec_yc.append({'Thoi_gian': tg, 'EC_YC': ec_val})
                except ValueError: pass
        lich_su_ec_yc.sort(key=lambda x: x['Thoi_gian'])

        # Gom dữ liệu tưới
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

        # =========================================================================================
        # ✂️ [NOTE QUAN TRỌNG]: KHÚC CHIA MÙA VỤ
        # =========================================================================================
        # Code duyệt qua các mốc thời gian. Nếu mốc sau cách mốc trước > SO_NGAY_CHUYEN_VU (2 ngày)
        # thì nó đóng gói mảng 'mua_hien_tai' lại và mở ra một mùa vụ mới.
        danh_sach_mua_vu = []
        mua_hien_tai = [du_lieu_da_loc[0]]
        
        for i in range(1, len(du_lieu_da_loc)):
            # TÍNH KHOẢNG CÁCH THỜI GIAN VÀ CẮT VỤ Ở ĐÂY 👇
            if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                danh_sach_mua_vu.append(mua_hien_tai) # Lưu vụ cũ
                mua_hien_tai = []                     # Reset để hứng vụ mới
            
            mua_hien_tai.append(du_lieu_da_loc[i])    # Nhét dữ liệu vào vụ hiện tại
            
        if mua_hien_tai: danh_sach_mua_vu.append(mua_hien_tai) # Lưu vụ cuối cùng
        # =========================================================================================


        ket_qua_bao_cao = []
        # Xử lý từng mùa vụ đã được cắt ở trên
        for mua_vu in danh_sach_mua_vu:
            ngay_bat_dau = mua_vu[0]['Thời gian']
            ngay_ket_thuc = mua_vu[-1]['Thời gian']
            
            # Nếu mùa vụ ngắn hơn 7 ngày (SO_NGAY_TOI_THIEU) thì vứt bỏ (Lọc rác)
            if (ngay_ket_thuc - ngay_bat_dau).days < SO_NGAY_TOI_THIEU: continue

            # =====================================================================================
            # ⏱️ [NOTE QUAN TRỌNG]: KHÚC TÍNH SỐ GIÂY TƯỚI THỰC TẾ
            # =====================================================================================
            cac_cu_tuoi = []; tg_bat = None; tong_lan = 0
            for dong in mua_vu:
                if dong['Trạng thái'] == 'Bật': 
                    tg_bat = dong['Thời gian'] # Đánh dấu lúc máy bơm Bật
                elif dong['Trạng thái'] == 'Tắt' and tg_bat is not None:
                    # Máy bơm Tắt -> Tính ra số giây đã chạy
                    giay_chay = (dong['Thời gian'] - tg_bat).total_seconds()
                    
                    # LỌC LỖI: Chỉ lấy các cữ tưới nằm trong khoảng giay_min và giay_max
                    if giay_min <= giay_chay <= giay_max:
                        cac_cu_tuoi.append({
                            'Ngày': tg_bat.date(), 'Giây chạy': giay_chay,
                            'EC_Yeu_Cau': dong['EC_Yeu_Cau'], 'EC_Thuc_Te': dong['EC_Thuc_Te'], 'pH': dong['pH']
                        })
                        tong_lan += 1
                    tg_bat = None
            # =====================================================================================

            # Thống kê gom nhóm lại theo từng Ngày
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
            
            # Tính trung bình mỗi ngày để chuẩn bị chia Giai đoạn
            ec_tt_vals = [thong_ke[n]['Tong_EC_TT'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            ec_yc_vals = [thong_ke[n]['Tong_EC_YC'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            tong_phut_vals = [thong_ke[n]['Tong_giay'] / 60 for n in danh_sach_ngay]
            
            # =====================================================================================
            # 🏷️ [NOTE QUAN TRỌNG]: KHÚC GỌI HÀM ĐỂ CHIA GIAI ĐOẠN 
            # =====================================================================================
            # Đưa các mảng giá trị trung bình vào hàm thuật toán ở trên cùng để nó dán nhãn GĐ 1, GĐ 2...
            stages_ec_tt = phan_tich_giai_doan_array(danh_sach_ngay, ec_tt_vals, ss_ec_tt, so_ngay_on_dinh)
            stages_ec_yc = phan_tich_giai_doan_array(danh_sach_ngay, ec_yc_vals, ss_ec_yc, so_ngay_on_dinh)
            stages_tuoi  = phan_tich_giai_doan_array(danh_sach_ngay, tong_phut_vals, ss_tong_phut, so_ngay_on_dinh)
            # =====================================================================================

            # Đóng gói dữ liệu ra dạng Bảng báo cáo
            bang_bao_cao_ngay = []
            for i, ngay in enumerate(danh_sach_ngay):
                bang_bao_cao_ngay.append({
                    "Ngày_Str": ngay.strftime("%d/%m/%Y"),
                    "GĐ_EC_Thực": f"GĐ {stages_ec_tt[ngay]}", # Lấy nhãn Giai đoạn đã chia ghép vào bảng
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
