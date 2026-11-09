"""R7.1 new-only regression; synthetic already-fetched HTML, no network/DB access."""
import unittest
from r71_photo_metadata_delta import propose_metadata_delta as propose

ARTICLE="https://www.dailygaewon.com/news/articleView.html?idxno=18647"
OLD="https://www.dailygaewon.com/news/thumbnail/202611/18647_26833_2154_v150.jpg"
NEW="https://www.dailygaewon.com/news/thumbnail/202611/18647_26866_1322_v150.jpg"

def og(url,prop="og:image"):
    return '<!doctype html><html><head><meta property="'+prop+'" content="'+url+'"></head></html>'

def case(**kw):
    p=dict(source_id="FEED_DAILYGAEWON", article_url=ARTICLE,page_status=200,
           page_content_type="text/html; charset=UTF-8", decoded_html=og(NEW),
           previous_photo_url=OLD, trigger="BROKEN_IMAGE", previous_failure="HTTP_404")
    p.update(kw)
    return propose(**p)

class R71PhotoDeltaTest(unittest.TestCase):
    def test_actual_18647_regression_exact_old_to_new(self):
        r=case()
        self.assertEqual(r["decision"],"REVIEW_REPAIRED_IMAGE_METADATA")
        self.assertEqual(r["candidateUrl"],NEW)
        self.assertEqual(r["replacedUrl"],OLD)
        self.assertEqual(r["articleNo"],"18647")
        self.assertFalse(r["publishable"])
        self.assertEqual(r["rightsStatus"],"PUBLISHER_PERMISSION_UNCONFIRMED")
        self.assertEqual(r["dbWrites"],0)
        self.assertEqual(r["imageFileDownloads"],0)

    def test_new_article_without_previous_photo(self):
        r=case(trigger="NEW_ARTICLE",previous_photo_url=None,previous_failure=None,
               article_url="https://www.dailygaewon.com/news/articleView.html?idxno=19000",
               decoded_html=og("https://www.dailygaewon.com/news/thumbnail/202611/19000_555_123_v150.jpg"))
        self.assertEqual(r["decision"],"REVIEW_NEW_IMAGE_METADATA")
        self.assertEqual(r["articleNo"],"19000")

    def test_not_refetch_when_previous_url_still_same(self):
        self.assertEqual(case(decoded_html=og(OLD))["decision"],"HOLD_BROKEN_URL_STILL_CURRENT")

    def test_refuse_repair_without_documented_failure(self):
        self.assertEqual(case(previous_failure=None)["decision"],"REJECT_NO_PROVEN_PHOTO_FAILURE")

    def test_refuse_unknown_media_and_unapproved_article(self):
        self.assertEqual(case(source_id="REF_DAILYVET")["decision"],"REJECT_UNKNOWN_SOURCE_OR_ARTICLE")
        self.assertEqual(case(source_id="REF_HAPPYPET")["decision"],"REJECT_UNKNOWN_SOURCE_OR_ARTICLE")
        self.assertEqual(case(article_url=ARTICLE+"&other=1")["decision"],"REJECT_UNKNOWN_SOURCE_OR_ARTICLE")

    def test_refuse_wrong_article_photo_even_same_domain(self):
        self.assertEqual(case(decoded_html=og(NEW.replace("/18647_","/18646_")))["decision"],
                         "HOLD_NO_SAFE_ARTICLE_IMAGE")

    def test_cross_site_and_unsafe_url_fail_closed(self):
        bad=[
            NEW.replace("www.dailygaewon.com","cdn.other-provider.com"),
            NEW.replace("https://","http://"),
            NEW+"?download=1",
            NEW.replace(".jpg",".svg"),
            NEW.replace("dailygaewon.com/","dailygaewon.com:invalid/"),
            "javascript:alert(1)"
        ]
        for link in bad:
            with self.subTest(url=link):
                self.assertEqual(case(decoded_html=og(link))["decision"],"HOLD_NO_SAFE_ARTICLE_IMAGE")

    def test_refuse_ambiguous_photos_for_one_article(self):
        html=og(NEW)+og(NEW.replace("_1322_","_1323_"))
        self.assertEqual(case(decoded_html=html)["decision"],"HOLD_MULTIPLE_MATCHING_IMAGES")

    def test_non200_and_non_html_and_lossy_text_fail_closed(self):
        self.assertEqual(case(page_status=403)["decision"],"HOLD_PAGE_NOT_200")
        self.assertEqual(case(page_content_type="image/jpeg")["decision"],"HOLD_NON_HTML_PAGE")
        self.assertEqual(case(decoded_html=og(NEW)+"\ufffd")["decision"],"HOLD_LOSSY_DECODE")
        self.assertEqual(case(decoded_html="a"*1_500_001)["decision"],"HOLD_UNSAFE_OR_OVERSIZED_HTML")

    def test_no_og_image_is_not_approved(self):
        self.assertEqual(case(decoded_html="<html><head><title>Article 18647</title></head></html>")["decision"],
                         "HOLD_NO_SAFE_ARTICLE_IMAGE")

    def test_reject_invalid_trigger_or_conflicting_new_article(self):
        self.assertEqual(case(trigger="RECOLLECT_ALL")["decision"],"REJECT_UNAPPROVED_TRIGGER")
        self.assertEqual(case(trigger="NEW_ARTICLE")["decision"],"REJECT_NEW_ARTICLE_WITH_EXISTING_PHOTO")

    def test_safe_relative_og_image_url(self):
        relative="/news/thumbnail/202611/18647_26866_1322_v150.jpg"
        self.assertEqual(case(decoded_html=og(relative,"og:image:secure_url"))["candidateUrl"],NEW)

    def test_duplicate_matching_meta_is_not_ambiguous(self):
        self.assertEqual(case(decoded_html=og(NEW)+og(NEW,"og:image:url"))["candidateUrl"],NEW)

    def test_only_url_metadata_not_article_body_is_returned(self):
        body="보호자 개인정보나 뉴스 원문 본문이 통째로 들어와도 결과에 복제하지 않음"
        r=case(decoded_html=og(NEW)+"<article>"+body+"</article>")
        self.assertNotIn(body,str(r))
        self.assertNotIn("decoded_html",r)

if __name__=="__main__":
    unittest.main()
