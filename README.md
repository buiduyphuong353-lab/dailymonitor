[BÁO CÁO TRÍCH XUẤT DỮ LIỆU (1).md](https://github.com/user-attachments/files/26769173/BAO.CAO.TRICH.XU.T.D.LI.U.1.md)
**BÁO CÁO TRÍCH XUẤT DỮ LIỆU**

**1. Đặt vấn đề và mục tiêu**

**1.1 Bối cảnh vận hành hệ thống tưới và châm phân hiện tại**

Trong xu hướng chuyển đổi số và tự động hóa quy trình sản xuất nông nghiệp hiện nay, việc ứng dụng các thiết bị tưới nhỏ giọt và châm phân tự động đang đóng vai trò cốt lõi. Về mặt lý thuyết, các hệ thống này được thiết kế và đưa vào vận hành với mục tiêu tự động hóa hoàn toàn việc kiểm soát khối lượng nước tưới cũng như nồng độ dinh dưỡng (chỉ số EC). Quá trình này được kỳ vọng sẽ đáp ứng nghiêm ngặt và chính xác bộ thông số nông sinh học đã được thiết lập riêng cho từng giai đoạn sinh trưởng của cây trồng.

Tuy nhiên, qua công tác thu thập dữ liệu và đánh giá hiệu năng thực tế của các hệ thống đang vận hành, có thể nhận thấy một số vấn đề rủi ro kỹ thuật cần được phân tích làm rõ:

* Có sự sai lệch giữa EC Yêu cầu (thông số cấu hình trên phần mềm) và EC Thực tế (nồng độ hòa trộn thực tế đẩy ra vườn), đặc biệt ở các chu kỳ cây trồng đòi hỏi mức dinh dưỡng cao.
* Việc xử lý các tệp dữ liệu thô xuất ra từ thiết bị vẫn gặp nhiều hạn chế. Dữ liệu thường chứa lượng lớn thông tin nhiễu (cữ tưới lỗi, thời gian bơm bất thường), gây khó khăn cho việc đánh giá độ ổn định của hệ thống bơm và bộ châm phân nếu không có thuật toán lọc chuyên dụng."

**1.2 Mục tiêu của việc phân tích**

Xuất phát từ bối cảnh trên, việc xây dựng một bộ công cụ tự động lọc dữ liệu và xuất báo cáo phân tích là cấp thiết. Mục tiêu cụ thể của báo cáo đợt này bao gồm:

1. Làm sạch và chuẩn hóa dữ liệu: Loại bỏ các dữ liệu rác (cữ tưới lỗi, test máy, thời gian tưới bất thường) để tái tạo lại lịch sử các mùa vụ hợp lệ một cách chính xác nhất.
2. Đánh giá mức độ tương thích của thiết bị: So sánh đối chiếu trực tiếp giữa cấu hình tưới lý thuyết và thực tế vận hành (Tập trung vào chỉ số EC và số cữ tưới/ngày) nhằm xác định tỷ lệ sai số của hệ thống châm phân.
3. Truy tìm nguyên nhân gốc rễ :Dựa vào biến động dữ liệu để xác định các nguyên nhân gây tụt/lệch EC là do phần cứng (bơm, cảm biến, tắc nghẽn đường ống) hay do lỗi thuật toán/cài đặt phần mềm.
4. Tối ưu hóa vận hành: Đề xuất các ngưỡng cảnh báo (ví dụ: EC tụt dưới 0.8) và điều chỉnh lại quy trình châm phân cho các mùa vụ tiếp theo để đảm bảo năng suất cây trồng.

**2. Phương pháp thu thập và xử lý dữ liệu**

**2.1 Nguồn dữ liệu đầu vào**

Dữ liệu phân tích được trích xuất trực tiếp từ bộ nhớ lưu trữ của bộ điều khiển trung tâm. Tập dữ liệu thô bao gồm hai luồng thông tin độc lập được máy tự động ghi nhận theo thời gian thực (real-time):

* Dữ liệu vận hành bơm (Lịch tưới): Lưu trữ các mốc thời gian hệ thống kích hoạt, bao gồm thời điểm bắt đầu, kết thúc và tổng thời lượng của từng cữ tưới.
* Dữ liệu thông số dinh dưỡng (Châm phân): Lưu trữ các chỉ số cần lọc(EC) tại thời điểm máy hoạt động, trọng tâm là sự đối chiếu giữa nồng độ dinh dưỡng được lập trình cài đặt (EC Yêu cầu) và nồng độ cảm biến đo được tại đường ống hòa trộn (EC Thực tế).

![](data:image/png;base64...)

Hình 1 Lưu đồ thuật toán lấy dữ liệu thô

**2.2 Tiêu chí tiền xử lý và làm sạch dữ liệu**

Trong thực tế vận hành, các tệp dữ liệu thô luôn chứa một tỷ lệ nhất định các bản ghi nhiễu (noise) sinh ra từ các thao tác kiểm tra máy định kỳ (test bơm), bảo trì, hoặc độ trễ của cảm biến. Để đảm bảo độ chính xác cho báo cáo, một thuật toán tiền xử lý đã được áp dụng để làm sạch dữ liệu dựa trên các tiêu chí sau:

* Sàng lọc theo thời lượng: Loại bỏ hoàn toàn các cữ tưới có thời gian hoạt động bất thường, bao gồm các cữ quá ngắn (thao tác nhấp nhả thiết bị) hoặc quá dài (lỗi treo phần mềm/phần cứng).
* Sàng lọc theo ngưỡng nồng độ (EC): Loại trừ các bản ghi có giá trị EC thực tế bằng 0 hoặc nằm dưới ngưỡng tối thiểu cho phép (ví dụ: EC < 0.8). Các bản ghi này thường đại diện cho quy trình tưới xả đường ống hoặc tưới nước tinh khiết không qua bộ châm phân.

![](data:image/png;base64...)

Hình 2 Lưu đồ thuật toán lọc dữ liệu

**2.3 Thuật toán nhận diện và phân tách mùa vụ**

Sau khi được làm sạch và ghép nối đồng bộ giữa thời gian bơm - chỉ số châm phân, tập dữ liệu tổng sẽ được đưa qua thuật toán phân tách để tự động nhận diện các chu kỳ nuôi trồng (được gọi là các "mùa vụ" hợp lệ). Việc định nghĩa một mùa vụ dựa trên các quy tắc logic:

* Nguyên tắc gián đoạn chu kỳ: Nếu khoảng thời gian trống giữa hai cữ tưới liên tiếp vượt quá giới hạn ngày cho phép (ngưỡng ngày nghỉ), thuật toán sẽ đánh dấu đó là điểm kết thúc của chu kỳ trước và bắt đầu một chu kỳ mới.
* ![](data:image/png;base64...)Nguyên tắc mật độ dữ liệu: Một chu kỳ thời gian chỉ được thuật toán công nhận là một "mùa vụ hợp lệ" để đưa vào báo cáo phân tích khi nó chứa đủ số lượng cữ tưới tối thiểu theo quy định và thể hiện được sự biến thiên của chỉ số EC qua nhiều giai đoạn sinh trưởng khác nhau.

Hình 3 Thuật toán xác định mùa vụ

**2.4** **Thuật toán phân chia giai đoạn sinh trưởng**

**![](data:image/png;base64...)**Sau khi một chu kỳ được xác nhận là "mùa vụ hợp lệ", hệ thống sẽ tiến hành chia nhỏ toàn bộ dải thời gian của mùa vụ đó thành các giai đoạn nhỏ hơn (tương ứng với các pha sinh trưởng của cây trồng). Quá trình dán nhãn (labeling) giai đoạn được thực hiện tự động nhằm phục vụ cho việc phân tích sâu, so sánh chéo hiệu năng thiết bị giữa các thời kỳ khác nhau.

Hình 4 Thuật toán chia giai đoạn

**3. Thiết kế giao diện người dùng**

**3.1 Các bước để tạo giao diện**

**Bước 1**: Tạo tài khoản người dùng
-Truy cập vào Streamlit.io để tạo tài khoản người dùng

![](data:image/png;base64...)

![](data:image/png;base64...)

Hình 5 Giao diện Web Streamlit

- Truy cập vào Github.com để tạo tài khoản người dùng

![](data:image/png;base64...)

Hình 6 Giao diện của Github

**Bước 2**: Tạo dự án và liên kết 2 nền tảng( Github và Streamlit)

-Tạo dự án trong Github

![](data:image/png;base64...)

![](data:image/png;base64...)

Hình 7 Tạo dự án trên Github

-Từ dự án đã tạo, tải file code chính để liên kết với Streamlit tạo giao diện(.py) và thêm 1 file để thêm các thư viện cần thiết(.txt)

![](data:image/png;base64...)

-Streamlit bấm vào Create app để tạo dự án.

![](data:image/png;base64...)

Hình 8 Tạo dự án ở Streamlit

-Chọn vào mục Deploy a public app from Github

-Chọn chọn dự án (Repository) đã tạo bên Github cho Streamlit, thêm các nhánh và code .py và deploy để tạo giao diện app

![](data:image/png;base64...)

![](data:image/png;base64...)

Hình 9 Liên kết 2 nền tảng để tạo giao diện

![](data:image/png;base64...)

Hình 10 Giao diện app khi dã hoàn tất

**4. Kết quả phân tích**

**4.1. Kết quả thống kê tổng quan**

Thuật toán phân tách mùa vụ đã nhận diện thành công chu kỳ sinh trưởng của Vụ 1 của khu vực 2 (từ 10/12 đến 10/02). Các chỉ số KPI tổng quan cho thấy hệ thống cơ điện (bơm, van) hoạt động với tần suất ổn định:

* Tổng thời gian vụ: 63 ngày.
* Số giai đoạn sinh trưởng: Thuật toán (với sai số cắt GĐ $\Delta = 0.15$) đã bóc tách thành công quá trình sinh trưởng thành 12 Giai đoạn (GĐ).
* Tần suất tưới trung bình: Đạt mức 6 lần/ngày, thời lượng mỗi cữ tưới dao động từ 20 đến 50 phút, đảm bảo độ ẩm liên tục cho giá thể.
* Chỉ số TBEC (Thực tế) trung bình: Đạt 1.21 cho toàn vụ.

**4.2. Phân tích biến thiên dinh dưỡng qua biểu đồ**

Quan sát biểu đồ "Phân tích theo: TBEC", hệ thống châm phân đã bám sát được chu trình sinh lý học của cây trồng với đường cong dinh dưỡng rất rõ ràng:

* Pha khởi tạo (GĐ 1 đến GĐ 3 | 10/12 - 28/12): Nồng độ TBEC được duy trì ở mức thấp, dao động trong khoảng 0.25 - 0.75. Đây là mức an toàn cho bộ rễ non của cây.
* Pha phát triển (GĐ 4 đến GĐ 8 | 30/12 - 27/01): Chỉ số TBEC tăng trưởng theo hình bậc thang, từ 0.75 vươn lên mức 1.75. Hệ thống phản hồi tốt với nhu cầu dinh dưỡng tăng cao.
* Pha đỉnh điểm (GĐ 9 đến GĐ 11 | 29/01 - 06/02): TBEC đạt đỉnh, liên tục duy trì ở mức cao trên 1.90, có những ngày vượt ngưỡng 2.00.
* Pha thu hoạch/Cuối vụ (GĐ 12 | 08/02 - 10/02): Nồng độ TBEC chủ động được giảm mạnh xuống dưới mức 0.75 (quá trình xả nước hoặc siết dinh dưỡng trước thu hoạch).

**4.3. Đánh giá rủi ro và Phát hiện lỗi hệ thống**

Mặc dù hệ thống cơ học bơm tưới hoạt động tốt, tính năng trích xuất "Bảng Số Liệu Chi Tiết" của Tool UI đã bộc lộ một lỗ hổng trong việc ghi nhận dữ liệu (Data Logging):

* Mất đồng bộ dữ liệu cấu hình (Missing Setpoint Data): Tại bảng số liệu chi tiết (từ ngày 06/01 đến 15/01 thuộc GĐ 4, 5, 6), trong khi hệ thống đo lường thực tế (TBEC) vẫn ghi nhận các chỉ số bình thường (như 0.90, 1.33, 1.91), thì cột EC YÊU CẦU lại liên tục trả về giá trị 0.000000.
* Nguyên nhân tiềm năng: 1. Tệp log lịch nho giotj.json (hoặc tệp châm phân) không trích xuất được tham số cài đặt từ bộ điều khiển trung tâm (PLC/Controller). 2. Kỹ thuật viên đã vận hành hệ thống ở chế độ "Thủ công" (Manual Mode) thay vì "Tự động" (Auto Mode), dẫn đến việc máy bơm vẫn chạy, cảm biến vẫn đo, nhưng phần mềm không ghi nhận được công thức mục tiêu.
* Hậu quả: Việc thiếu hụt dữ liệu EC YÊU CẦU khiến các thuật toán cảnh báo sai số không thể tính toán được độ lệch giữa thực tế và lý thuyết, gây khó khăn cho việc đánh giá chất lượng hòa trộn phân.

**5. Kết luận và đề xuất hướng phát triển**

**5.1 Kết luận**

Phân tích tập dữ liệu vận hành thông qua hệ thống phần mềm cho thấy cụm thiết bị bơm tưới và châm phân tự động cơ bản đáp ứng được yêu cầu sinh lý của cây trồng. Chu trình biến thiên nồng độ dinh dưỡng (TBEC) tuân thủ chặt chẽ và phản ánh đúng mức độ hấp thụ theo từng giai đoạn sinh trưởng.

Tuy nhiên, qua quá trình tiền xử lý và bóc tách dữ liệu, đã phát hiện ra lỗ hổng trong khâu thu thập và lưu trữ tín hiệu. Cụ thể, hiện tượng mất đồng bộ tham số cài đặt (EC Yêu cầu) tại một số giai đoạn đã gây đứt gãy chuỗi dữ liệu đối chứng, làm hạn chế khả năng tính toán sai số hòa trộn của hệ thống tự động.

**5.2 Định hướng phát triển**

Tích hợp thuật toán phát hiện bất thường: Đề xuất nâng cấp công cụ phân tích bằng việc bổ sung các hàm kiểm tra tính toàn vẹn của dữ liệu. Cụ thể, thiết lập cơ chế cảnh báo tự động khi phát hiện các cặp giá trị phi logic (Ví dụ: Thực tế TBEC > 0.5 nhưng Cấu hình EC Yêu cầu = 0.0), giúp chuyên gia phân tích nhanh chóng nhận diện và cách ly các bản ghi lỗi.

Xây dựng lịch hiệu chuẩn dựa trên phân rã chu kỳ: Thay vì bảo trì theo cảm tính, cần ứng dụng tính năng truy vết và phân rã dữ liệu theo giai đoạn sinh trưởng để lên lịch bảo dưỡng. Khuyến nghị tiến hành hiệu chuẩn cảm biến đo lường và vệ sinh hệ thống ống tại các mốc chuyển giao sinh lý quan trọng (đặc biệt là trước pha tăng tốc dinh dưỡng) nhằm triệt tiêu sai số cộng dồn do mảng bám hóa chất tích tụ lâu ngày.

Nghiên cứu tích hợp các mô hình học máy để tự động nhận diện quy luật sinh trưởng và dự đoán nhu cầu dinh dưỡng của cây trồng dựa trên cơ sở dữ liệu lịch sử. Việc ứng dụng AI sẽ giúp hệ thống chuyển đổi từ trạng thái phản hồi thụ động sang chủ động đưa ra các khuyến nghị vận hành tối ưu, cảnh báo sớm các rủi ro về bệnh dịch hoặc suy dinh dưỡng, từ đó tối đa hóa năng suất và tiết kiệm tài nguyên.
## 图片内容
[检测到图片但LLM不可用，无法识别内容]
