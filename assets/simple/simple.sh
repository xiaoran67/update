# 1. 批量处理所有 .txt（和原版脚本 input_dir 一致）
for file in /storage/emulated/0/.subscribe-main/output/*.txt; do
  # 2. 按 #genre# 分组不打乱，相同直播源保留3个（匹配原版 process_file 逻辑）
  awk -F ',' '
    /,#genre#/ { print; next }  # 分组行直接保留
    { 
      name = $1; 
      if (!seen[name]) { seen[name]=1; print } 
      else if (seen[name] < 3) { seen[name]++; print } 
    }
  ' "$file" > "/storage/emulated/0/.subscribe-main/output/simple/$(basename "$file")"
done

# 3. 输出目录和原版一致（output/simple），手机文件管理器直接查看
ls /storage/emulated/0/.subscribe-main/output/simple
