import os
import json
from PIL import Image
import numpy as np
from pathlib import Path

# 画像の品質を評価する関数
def evaluate_image_quality(img_path):
    try:
        img = Image.open(img_path)
        img_array = np.array(img)
        
        # 全てのピクセルが0（真っ黒）の場合
        is_black = np.all(img_array == 0)
        
        # 平均値と標準偏差を計算
        mean_value = np.mean(img_array)
        std_dev = np.std(img_array)
        
        return {
            'is_black': is_black,
            'mean_value': mean_value,
            'std_dev': std_dev
        }
    except Exception as e:
        print(f"画像の読み込みに失敗: {img_path}")
        return None

def main():
    # メタデータの読み込み
    metadata_path = Path('satellite_metadata.json')
    if not metadata_path.exists():
        print("メタデータファイルが見つかりません")
        return
    
    with open(metadata_path, 'r') as f:
        metadata_list = json.load(f)
    
    # 画像ディレクトリの確認
    images_dir = Path('satellite_images')
    if not images_dir.exists():
        print("画像ディレクトリが見つかりません")
        return
    
    # プラットフォームごとの統計情報
    platform_stats = {
        'sentinel-2a': {'count': 0, 'black_count': 0, 'mean_values': [], 'std_devs': []},
        'sentinel-2b': {'count': 0, 'black_count': 0, 'mean_values': [], 'std_devs': []},
        'sentinel-2c': {'count': 0, 'black_count': 0, 'mean_values': [], 'std_devs': []}
    }
    
    # 全てのメタデータに対して処理
    for meta in metadata_list:
        date_str = meta['datetime'][:10]
        platform = meta['platform'].lower()
        img_path = images_dir / f'satellite_{date_str}.png'
        
        if not img_path.exists():
            continue
            
        # 画像の品質評価
        quality = evaluate_image_quality(img_path)
        if quality is None:
            continue
        
        # 統計情報の更新
        stats = platform_stats[platform]
        stats['count'] += 1
        if quality['is_black']:
            stats['black_count'] += 1
        stats['mean_values'].append(quality['mean_value'])
        stats['std_devs'].append(quality['std_dev'])
    
    # 結果の表示
    print("\nプラットフォームごとの画像品質の統計情報:")
    for platform, stats in platform_stats.items():
        if stats['count'] == 0:
            continue
            
        print(f"\nプラットフォーム: {platform}")
        print(f"総画像数: {stats['count']}")
        print(f"真っ黒な画像数: {stats['black_count']}")
        print(f"真っ黒な画像の割合: {stats['black_count']/stats['count']:.2%}")
        print(f"平均値の平均: {np.mean(stats['mean_values']):.2f}")
        print(f"標準偏差の平均: {np.mean(stats['std_devs']):.2f}")

if __name__ == '__main__':
    main()
