/**
 * Verb configuration registry — maps each PlayerVerb to its VerbConfig.
 */

import type { VerbConfig } from "./types";
import { educateConfig } from "./educate";
import { aidConfig } from "./aid";
import { attackConfig } from "./attack";
import { mobilizeConfig } from "./mobilize";
import { campaignConfig } from "./campaign";
import { moveConfig } from "./move";
import { investigateConfig } from "./investigate";
import { reproduceConfig } from "./reproduce";
import { negotiateConfig } from "./negotiate";

export const VERB_REGISTRY: Record<string, VerbConfig> = {
  educate: educateConfig,
  aid: aidConfig,
  attack: attackConfig,
  mobilize: mobilizeConfig,
  campaign: campaignConfig,
  move: moveConfig,
  investigate: investigateConfig,
  reproduce: reproduceConfig,
  negotiate: negotiateConfig,
};

/** Sorted list of all registered verb names. */
export const VERB_NAMES = Object.keys(VERB_REGISTRY).sort();
