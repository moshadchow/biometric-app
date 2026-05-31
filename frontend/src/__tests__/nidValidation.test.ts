import { describe, expect, it } from "vitest";
import { extractNIDData } from "@/services/nidValidation.service";

describe("extractNIDData", () => {
  it("extracts father and mother from explicit Bengali labels", () => {
    const frontText = [
      "জাতীয় পরিচয়পত্র",
      "নাম: মোঃ রহিম উদ্দিন",
      "পিতা: আব্দুল করিম",
      "মাতা: রোকেয়া বেগম",
      "Date of Birth: 12 Jan 1990",
    ].join("\n");

    const result = extractNIDData(frontText);

    expect(result.fields.fatherName).toBe("আব্দুল করিম");
    expect(result.fields.motherName).toBe("রোকেয়া বেগম");
    expect(result.fieldMeta.fatherName?.labelVerified).toBe(true);
    expect(result.fieldMeta.motherName?.labelVerified).toBe(true);
  });

  it("extracts father's name from Bangla 'পিতার নাম' label on the front page", () => {
    const frontText = [
      "জাতীয় পরিচয়পত্র",
      "নাম: মোঃ রহিম উদ্দিন",
      "পিতার নাম: আব্দুল করিম",
      "মাতার নাম: রোকেয়া বেগম",
      "Date of Birth: 12 Jan 1990",
    ].join("\n");

    const result = extractNIDData(frontText);

    expect(result.fields.fatherName).toBe("আব্দুল করিম");
    expect(result.fieldMeta.fatherName?.labelVerified).toBe(true);
    expect(result.fieldMeta.fatherName?.source).toBe("bengali_label");
  });

  it("joins wrapped Bangla mother's name lines from the front page", () => {
    const frontText = [
      "জাতীয় পরিচয়পত্র",
      "নাম: মোঃ রহিম উদ্দিন",
      "পিতার নাম: আব্দুল করিম",
      "মাতার নাম: রোকেয়া",
      "বেগম",
      "Date of Birth: 12 Jan 1990",
    ].join("\n");

    const result = extractNIDData(frontText);

    expect(result.fields.motherName).toBe("রোকেয়া বেগম");
    expect(result.fieldMeta.motherName?.labelVerified).toBe(true);
    expect(result.fieldMeta.motherName?.source).toBe("bengali_label");
  });

  it("extracts parent names from English labels", () => {
    const frontText = [
      "NATIONAL ID CARD",
      "Name: MD RAHIM UDDIN",
      "Father's Name: ABDUL KARIM",
      "Mother's Name: ROKEYA BEGUM",
      "Date of Birth: 12 Jan 1990",
    ].join("\n");

    const result = extractNIDData(frontText);

    expect(result.fields.fatherName).toBe("ABDUL KARIM");
    expect(result.fields.motherName).toBe("ROKEYA BEGUM");
    expect(result.fieldMeta.fatherName?.source).toBe("english_label");
    expect(result.fieldMeta.motherName?.source).toBe("english_label");
  });

  it("does not guess parent names when positional fallback is ambiguous", () => {
    const frontText = [
      "জাতীয় পরিচয়পত্র",
      "নাম: মোঃ রহিম উদ্দিন",
      "আব্দুল করিম",
      "রোকেয়া বেগম",
      "অতিরিক্ত শব্দ",
      "Date of Birth: 12 Jan 1990",
    ].join("\n");

    const result = extractNIDData(frontText);

    expect(result.fields.fatherName).toBeUndefined();
    expect(result.fields.motherName).toBeUndefined();
  });

  it("extracts district from explicit label in the address block", () => {
    const backText = [
      "ঠিকানা: বাড়ি ১২, সড়ক ৫",
      "ডাকঘর: গুলশান ১২১২",
      "জেলা: ঢাকা",
      "প্রদানকারী",
    ].join("\n");

    const result = extractNIDData("Name: TEST", backText);

    expect(result.fields.district).toBe("ঢাকা");
    expect(result.fieldMeta.district?.labelVerified).toBe(true);
  });

  it("uses bounded address fallback for district", () => {
    const backText = [
      "ঠিকানা: বাড়ি ১২",
      "১২১২, গুলশান, ঢাকা",
      "প্রদানকারী",
    ].join("\n");

    const result = extractNIDData("Name: TEST", backText);

    expect(result.fields.district).toBe("ঢাকা");
    expect(result.fieldMeta.district?.source).toBe("address_structure");
    expect(result.fieldMeta.district?.labelVerified).toBe(false);
  });

  it("does not use unrelated trailing Bengali text as district", () => {
    const backText = [
      "ঠিকানা: বাড়ি ১২",
      "লাইন ভাঙা লেখা",
      "প্রদানকারী",
    ].join("\n");

    const result = extractNIDData("Name: TEST", backText);

    expect(result.fields.district).toBeUndefined();
  });
});
