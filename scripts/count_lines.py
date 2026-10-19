import glob

files = sorted(glob.glob('src/**/*.vl', recursive=True))
file_counts = [(f, sum(1 for _ in open(f, encoding='utf-8'))) for f in files]
file_counts.sort(key=lambda x: x[1], reverse=True)

for path, count in file_counts:
    status = "OK" if count < 400 else "OVER LIMIT!"
    print(f"{count:3d}  {status:11s}  {path}")
