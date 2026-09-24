from src.interface.tv_selection_mobile_feedback import TVSelectionMobileFeedbackIngestor


_PLATFORMS={"ios","android"}


class TVSelectionNativeFeedbackAdapter:
    """Narrow profile-bound feedback bridge for native mobile clients."""

    __slots__=("_ingestor","platform")

    def __init__(self,store,*,platform,authorized_profile_id):
        if type(platform) is not str or platform not in _PLATFORMS:
            raise ValueError("unsupported native platform")
        self.platform=platform
        self._ingestor=TVSelectionMobileFeedbackIngestor(store,authorized_profile_id=authorized_profile_id)

    def sync(self,payload):
        if type(payload) is not dict or set(payload)!={"events"}:
            raise ValueError("invalid native feedback synchronization payload")
        return self._ingestor.ingest_batch(payload["events"])

    def handle(self,payload):
        try:
            result=self.sync(payload)
        except ValueError as error:
            code="PROFILE_NOT_AUTHORIZED" if str(error)=="mobile feedback profile is not authorized" else "INVALID_FEEDBACK"
            return {"schema_version":1,"ok":False,"error":{"code":code}}
        return {"schema_version":1,"ok":True,**result}
