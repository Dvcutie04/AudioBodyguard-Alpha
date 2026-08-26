    def test_raw_audio_field_is_impossible(self):
        obs = AcousticObservation(**self.valid_kwargs)
        
        # Verify slots block new dynamic attributes
        with self.assertRaises(AttributeError):
            setattr(obs, "raw_audio", b"10101010")
            
        # Verify frozen constraints block setting existing fields
        with self.assertRaises(AttributeError):
            setattr(obs, "spl_estimate", 70.0)
