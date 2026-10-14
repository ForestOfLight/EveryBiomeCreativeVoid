import { CommandPermissionLevel, CustomCommandParamType, CustomCommandSource, CustomCommandStatus, DimensionTypes, system, world } from "@minecraft/server"
import { biomes } from "./biomes"

const command = {
    name: 'everybiomecreative:biometp',
    description: "Teleports you to Every Biome Creative's dimension of the specified biome.",
    mandatoryParameters: [{ enumName: 'biome', name: 'everybiomecreative:biome', type: CustomCommandParamType.Enum }],
    permissionLevel: CommandPermissionLevel.Any
};

system.beforeEvents.startup.subscribe((event) => {
    const commandRegistry = event.customCommandRegistry;
    commandRegistry.registerEnum('everybiomecreative:biome', getAllDimensionIds());
    commandRegistry.registerCommand(command, biometpCommand);
});

function biometpCommand(origin, biomeId) {
    if (origin.sourceType !== CustomCommandSource.Entity)
        return { status: CustomCommandStatus.Failure, message: `This command can only be run by entities.` };
    if (!getAllDimensionIds().includes(biomeId))
        return { status: CustomCommandStatus.Failure, message: `Invalid biome id: "${biomeId}"` };

    const dimensionId = biomeId.includes('minecraft:') ? biomeId : "everybiomecreative:" + biomeId;
    const entity = origin.sourceEntity;
    system.run(() => entity.teleport(entity.location, { dimension: world.getDimension(dimensionId) }));
    return { status: CustomCommandStatus.Success, message: `Teleported to ${biomeId} dimension.` };
}

function getAllDimensionIds() {
    // DimensionTypes.getAll() only includes custom dimensions after startup, so this function is a workaround that works both during startup and after. 
    const biomeIds = getAllBiomeIds();
    biomeIds.push(...getVanillaDimensionIds());
    return biomeIds;
}

function getVanillaDimensionIds() {
    return DimensionTypes.getAll().map(dimensionType => dimensionType.typeId).filter(dimensionId => dimensionId.startsWith('minecraft:'));
}

function getAllBiomeIds() {
    return biomes.map(biomeData => biomeData.biomeId.replace('minecraft:', ''));
}