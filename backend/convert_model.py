import json
import numpy as np
import tensorflow as tf

def convert_tfjs_to_keras(model_json_path, output_dir):
    """Конвертирует TFJS модель в Keras SavedModel"""
    
    # Загружаем JSON
    with open(model_json_path, 'r') as f:
        model_json = json.load(f)
    
    # Создаем модель из топологии
    model = tf.keras.models.model_from_json(json.dumps(model_json['modelTopology']))
    
    # Загружаем веса
    weights = []
    base_dir = '/'.join(model_json_path.split('/')[:-1]) + '/'
    
    for weight_info in model_json['weightsManifest'][0]['weights']:
        weight_name = weight_info['name']
        weight_shape = weight_info['shape']
        
        # Ищем бинарный файл
        bin_file = weight_info['paths'][0]
        bin_path = base_dir + bin_file
        
        # Загружаем бинарные данные
        weight_data = np.fromfile(bin_path, dtype=np.float32)
        
        # Изменяем форму
        weight_tensor = weight_data.reshape(weight_shape)
        weights.append(weight_tensor)
    
    # Устанавливаем веса в модель
    model.set_weights(weights)
    
    # Сохраняем в формате SavedModel
    model.save(output_dir)
    print(f"✅ Модель сохранена в {output_dir}")
    
    # Пробуем загрузить обратно для проверки
    loaded = tf.keras.models.load_model(output_dir)
    print(f"✅ Проверка: модель загружена, вход: {loaded.input_shape}")
    
    return model

if __name__ == "__main__":
    # Конвертируем
    model = convert_tfjs_to_keras(
        'models/pieces_model/model.json',
        'models/pieces_model_saved'
    )
