Import("env")
import os

def make_merged_bin(source, target, env):
    # 1. On récupère dynamiquement TOUTES les images (bootloader, partitions, et le fameux boot_app0)
    flash_images = env.get("FLASH_EXTRA_IMAGES", [])
    
    # 2. On y ajoute ton firmware principal à l'adresse 0x10000
    app_offset = env.subst("$ESP32_APP_OFFSET")
    if not app_offset:
        app_offset = "0x10000"
    
    firmware_path = env.subst("$BUILD_DIR/${PROGNAME}.bin")
    
    images_to_merge = list(flash_images)
    images_to_merge.append((app_offset, firmware_path))
    
    # 3. On prépare les chemins pour la ligne de commande
    cmd_args = []
    for offset, path in images_to_merge:
        cmd_args.extend([offset, f'"{env.subst(path)}"'])
        
    images_str = " ".join(cmd_args)
    
    output = os.path.join(env.subst("$PROJECT_DIR"), "FIRMWARE_UNIQUE.bin")
    mcu = env.get("BOARD_MCU", "esp32c3")
    
    # 4. Récupération automatique du mode et de la vitesse de la mémoire flash
    flash_mode = env.get("BOARD_FLASH_MODE", "dio")
    freq_raw = env.get("BOARD_F_FLASH", "80000000L").replace("L", "")
    flash_freq = freq_raw.replace("000000", "m") # Transforme 80000000 en 80m
    
    cmd = f'"{env.subst("$PYTHONEXE")}" -m esptool --chip {mcu} merge_bin -o "{output}" --flash_mode {flash_mode} --flash_freq {flash_freq} --flash_size 4MB {images_str}'
    
    print("\n=======================================================")
    print("🪄 FUSION AVANCÉE DES BINAIRES (INCLUANT BOOT_APP0)...")
    env.Execute(cmd)
    print(f"✅ TERMINÉ ! Le fichier complet est prêt : {output}")
    print("=======================================================\n")

# Dit à PlatformIO de lancer ce script tout à la fin de la compilation
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", make_merged_bin)