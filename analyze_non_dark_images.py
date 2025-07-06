import json
import os
from PIL import Image
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple

def load_metadata() -> List[Dict]:
    """メタデータを読み込む"""
    with open('satellite_metadata.json', 'r') as f:
        return json.load(f)

def load_image(path: str) -> np.ndarray:
    """画像を読み込み、NumPy配列に変換"""
    img = Image.open(path)
    return np.array(img)

def analyze_image(img: np.ndarray) -> Dict:
    """画像の統計情報を計算"""
    # RGBチャンネルごとに分析
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    
    # 基本統計
    stats = {
        'mean': np.mean(img),
        'std': np.std(img),
        'min': np.min(img),
        'max': np.max(img),
        'r_mean': np.mean(r),
        'g_mean': np.mean(g),
        'b_mean': np.mean(b),
        'r_std': np.std(r),
        'g_std': np.std(g),
        'b_std': np.std(b)
    }
    
    # ヒストグラムの計算
    hist, bins = np.histogram(img.flatten(), bins=256, range=(0, 256))
    stats['histogram'] = hist.tolist()
    
    # 画像の明るさ分布の特徴
    stats['brightness_range'] = stats['max'] - stats['min']
    stats['high_brightness_ratio'] = np.sum(img > 200) / img.size
    stats['low_brightness_ratio'] = np.sum(img < 50) / img.size
    
    return stats

def analyze_time_series(metadata: List[Dict], stats_list: List[Dict]) -> Dict:
    """時間系列の分析"""
    time_series = {}
    for meta, stats in zip(metadata, stats_list):
        date = datetime.strptime(meta['datetime'], '%Y-%m-%dT%H:%M:%SZ')
        platform = meta['platform']
        
        if platform not in time_series:
            time_series[platform] = []
        
        time_series[platform].append({
            'date': date,
            'stats': stats
        })
    
    return time_series

def plot_analysis(stats: Dict, output_dir: str):
    """分析結果をプロット"""
    os.makedirs(output_dir, exist_ok=True)
    
    # ヒストグラムのプロット
    plt.figure(figsize=(12, 6))
    plt.hist(stats['histogram'], bins=256, range=(0, 256), density=True)
    plt.title('Pixel Value Distribution')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.savefig(f"{output_dir}/histogram.png")
    plt.close()
    
    # チャンネルごとの統計
    channel_stats = {
        'r': {'mean': stats['r_mean'], 'std': stats['r_std']},
        'g': {'mean': stats['g_mean'], 'std': stats['g_std']},
        'b': {'mean': stats['b_mean'], 'std': stats['b_std']}
    }
    
    with open(f"{output_dir}/channel_stats.json", 'w') as f:
        json.dump(channel_stats, f, indent=2)

def main():
    # メタデータの読み込み
    metadata = load_metadata()
    
    # 画像の読み込みと分析
    stats_list = []
    for meta in metadata:
        img_path = f"satellite_images/satellite_{meta['datetime'][:10]}.png"
        if not os.path.exists(img_path):
            continue
            
        img = load_image(img_path)
        stats = analyze_image(img)
        stats_list.append(stats)
    
    # 時間系列の分析
    time_series = analyze_time_series(metadata, stats_list)
    
    # プラットフォームごとの分析結果の保存
    for platform, data in time_series.items():
        platform_dir = f"analysis_results/{platform}"
        os.makedirs(platform_dir, exist_ok=True)
        
        # 統計の要約
        stats_summary = {
            'mean_brightness': np.mean([d['stats']['mean'] for d in data]),
            'std_brightness': np.std([d['stats']['mean'] for d in data]),
            'brightness_range': np.mean([d['stats']['brightness_range'] for d in data]),
            'high_brightness_ratio': np.mean([d['stats']['high_brightness_ratio'] for d in data]),
            'low_brightness_ratio': np.mean([d['stats']['low_brightness_ratio'] for d in data])
        }
        
        with open(f"{platform_dir}/stats_summary.json", 'w') as f:
            json.dump(stats_summary, f, indent=2)
        
        # プロットの作成
        plot_analysis(data[0]['stats'], platform_dir)

if __name__ == '__main__':
    main()
