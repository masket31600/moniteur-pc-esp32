Import("env")
import os

def make_merged_bin(source, target, env):
    print("\n=======================================================")
    print("🛠️  GÉNÉRATION DU FICHIER UNIQUE (MÉTHODE ABSOLUE)...")
    
    build_dir = env.subst("$BUILD_DIR")
    
    # 1. Récupération des 3 fichiers de base
    bootloader = os.path.join(build_dir, "bootloader.bin")
    partitions = os.path.join(build_dir, "partitions.bin")
    firmware   = os.path.join(build_dir, "firmware.bin")
    
    # 2. Récupération de boot_app0.bin (Chemin absolu infaillible)
    images = env.get("FLASH_EXTRA_IMAGES", [])
    boot_app0 = ""
    for offset, path in images:
        if "boot_app0" in path:
            boot_app0 = env.subst(path)
            
    if not boot_app0:
        framework_dir = env.PioPlatform().get_package_dir("framework-arduinoespressif32")
        boot_app0 = os.path.join(framework_dir, "tools", "partitions", "boot_app0.bin")
    
    output = os.path.join(env.subst("$PROJECT_DIR"), "FIRMWARE_UNIQUE.bin")
    
    # 3. Récupération de esptool.py (Chemin absolu infaillible)
    esptool_dir = env.PioPlatform().get_package_dir("tool-esptoolpy")
    esptool_path = os.path.join(esptool_dir, "esptool.py")
    
    # 4. La commande de fusion
    cmd = (f'"{env.subst("$PYTHONEXE")}" "{esptool_path}" --chip esp32c3 merge_bin '
           f'-o "{output}" --flash_mode dio --flash_freq 80m --flash_size 4MB '
           f'0x0000 "{bootloader}" 0x8000 "{partitions}" 0xe000 "{boot_app0}" 0x10000 "{firmware}"')
    
    env.Execute(cmd)
    print(f"✅ FUSION TERMINÉE ! Fichier : {output}")
    print("=======================================================\n")

env.AddPostAction("$BUILD_DIR/firmware.bin", make_merged_bin)