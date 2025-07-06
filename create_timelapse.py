import cv2
import os
from pathlib import Path
import json
from datetime import datetime

def create_timelapse(output_dir='output', output_file='timelapse.mp4', fps=3.33):
    """
    satellite_imagesディレクトリ内の画像からタイムラプス動画を作成します。
    cloud_coverが80%以上の画像はスキップします。
    
    Parameters:
    output_dir (str): 出力ディレクトリのパス
    output_file (str): 出力する動画ファイル名
    fps (float): フレームレート（1画像あたり0.3秒で表示するため、3.33fps）
    """
    # 出力ディレクトリの作成
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # メタデータの読み込み
    with open('satellite_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    # 画像ファイルのパスを取得
    images_dir = Path('satellite_images')
    image_files = sorted(images_dir.glob('*'))
    
    # cloud_coverが80%以上の画像を除外
    filtered_files = []
    skipped_count = 0
    for image_file in image_files:
        # ファイル名から日付を取得（例: satellite_2024-07-03.png）
        date_str = image_file.stem.split('_')[1]
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # メタデータから該当するエントリを検索
        for entry in metadata:
            entry_date = datetime.strptime(entry['datetime'][:10], '%Y-%m-%d')
            if entry_date == date:
                if entry['cloud_cover'] < 70:
                    filtered_files.append(image_file)
                else:
                    skipped_count += 1
                break
    
    image_files = filtered_files
    image_files = sorted(image_files)
    if skipped_count > 0:
        print(f"cloud_coverが80%以上の画像 {skipped_count}枚をスキップしました")
    if not image_files:
        print("エラー: 画像ファイルが見つかりません")
        return
    
    if not image_files:
        print("エラー: 画像ファイルが見つかりません")
        return
    
    print(f"{len(image_files)}枚の画像を処理します...")
    
    # 最初の画像のサイズを取得
    first_image = cv2.imread(str(image_files[0]))
    height, width = first_image.shape[:2]
    
    # ビデオライターの設定
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_video_path = output_path / output_file
    video_writer = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))
    
    # 画像を順番にビデオに追加
    for i, image_file in enumerate(image_files, 1):
        try:
            # 画像の読み込みと日付情報の取得
            frame = cv2.imread(str(image_file))
            # ファイル名から日付情報を抽出（例: 20250625_1200.png -> 2025/06/25 12:00）
            date_str = image_file.stem
            date_str = date_str.split('_')[1].replace(')', '')
            date_str = date_str.replace('-', '/')
            
            # 日付を画像に追加
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            color = (0, 0, 0)  # 白色
            
            # 日付の位置を計算（右端から少し左にずらす）
            text_size = cv2.getTextSize(date_str, font, font_scale, thickness)[0]
            text_x = width - text_size[0] - 10  # 右端から10ピクセル左
            text_y = height - 10  # 下端から10ピクセル上
            
            # 日付を描画
            cv2.putText(frame, date_str, (text_x, text_y), font, font_scale, color, thickness)
            
            video_writer.write(frame)
            print(f"処理中: {i}/{len(image_files)} ({i/len(image_files)*100:.1f}%)", end='\r')
        except Exception as e:
            print(f"エラー: {image_file.name}の処理中にエラーが発生しました: {str(e)}")
    
    # リソースの解放
    video_writer.release()
    print(f"\nタイムラプス動画が作成されました: {output_video_path}")
    print(f"動画のフレームレート: {fps:.2f} fps")
    print(f"動画のサイズ: {width}x{height} pixels")

if __name__ == '__main__':
    create_timelapse()
