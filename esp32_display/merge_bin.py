Import("env")
import os

def make_merged_bin(source, target, env):
    print("\n=======================================================")
    print("🛠️  GÉNÉRATION DU FICHIER UNIQUE (MODE SÉCURISÉ)...")
    
    build_dir = env.subst("$BUILD_DIR")
    
    # 1. Récupération des 3 fichiers de base
    bootloader = os.path.join(build_dir, "bootloader.bin")
    partitions = os.path.join(build_dir, "partitions.bin")
    firmware   = os.path.join(build_dir, "firmware.bin")
    
    # 2. Recherche du fichier caché boot_app0.bin
    images = env.get("FLASH_EXTRA_IMAGES", [])
    boot_app0 = ""
    for offset, path in images:
        if "boot_app0" in path:
            boot_app0 = env.subst(path)
            
    if not boot_app0:
        # Chemin de secours dans les dossiers de PlatformIO
        boot_app0 = os.path.join(env.subst("$PIOHOME_DIR"), "packages", "framework-arduinoespressif32", "tools", "partitions", "boot_app0.bin")
    
    output = os.path.join(env.subst("$PROJECT_DIR"), "FIRMWARE_UNIQUE.bin")
    
    # 3. La commande de fusion absolue
    cmd = (f'"{env.subst("$PYTHONEXE")}" -m esptool --chip esp32c3 merge_bin '
           f'-o "{output}" --flash_mode dio --flash_freq 80m --flash_size 4MB '
           f'0x0000 "{bootloader}" 0x8000 "{partitions}" 0xe000 "{boot_app0}" 0x10000 "{firmware}"')
    
    env.Execute(cmd)
    print(f"✅ FUSION TERMINÉE ! Fichier : {output}")
    print("=======================================================\n")

# On force l'exécution après la création du fichier .bin standard
env.AddPostAction("$BUILD_DIR/firmware.bin", make_merged_bin)