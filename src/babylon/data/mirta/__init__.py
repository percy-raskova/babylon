"""MIRTA (Military Installations, Ranges, and Training Areas) loaders.

Provides loaders for DoD military installation datasets via ArcGIS FeatureServer.

Data Source:
    https://www.acq.osd.mil/eie/BSI/BEI_MIRTA.html
"""

from babylon.data.mirta.loader import MIRTAMilitaryLoader

__all__ = ["MIRTAMilitaryLoader"]
