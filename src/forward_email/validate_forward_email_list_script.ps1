# 準備所有需要驗證的 email 列表，以 dev team 為例子
$emails = @(
    "shiunchiu.me@gmail.com",
    "ptqwe20020413@gmail.com",
    "harryup2000@gmail.com",
    "poyang1024@gmail.com",
    "tiffany.zsed18@gmail.com",
    "271yeye@gmail.com",
    "awseducate.cloudambassador+dev@gmail.com",

    # 預設收件者
    "awseducate.cloudambassador@gmail.com"
)

# 批次發送驗證郵件
foreach ($email in $emails) {
    Write-Host "Sending verification to: $email" -ForegroundColor Cyan
    aws ses verify-email-identity `
        --email-address $email `
        --profile tpet-aws-educate `
        --region ap-northeast-1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Sent to $email" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed for $email" -ForegroundColor Red
    }
}
