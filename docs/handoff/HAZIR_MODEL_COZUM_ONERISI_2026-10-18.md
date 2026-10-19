Kanka, çözüm yolunu senin tarif etmen gerekmiyor. Benim de sürekli “bir sonraki deneyi yapalım” demek yerine **hangi yaklaşıma yatırım yapmaya değer olduğunu belirlemem gerekiyor.**

**Benim önerim: mevcut LATE/COMBO yöntemini geliştirme odağından çıkaralım ve görüntüden bakış tahmini yapan hazır bir modeli temel alalım.** Eski yöntem karşılaştırma için kalsın.

Neden bu yönü öneriyorum? Şu an yüz ve gözlerden birkaç sayı çıkarıp bunları ekran koordinatına bağlıyoruz: iris konumu, göz açıklığı, blendshape ve baş açısı. Bu ölçümlerin farklı birleşimlerini denedik; kalibrasyon sonrasında kararlılık sorunu devam etti. İkinci kamera bazı oturumlarda yardımcı oldu ama Çağrı üzerinde güvenilir bir çözüm oluşturmadı. Artık aynı ölçümlerin ağırlıklarıyla uğraşmanın getirisi konusunda yeterince şüphemiz var.

Görüntüden çalışan bir bakış modeli ise yüzün veya gözlerin **görüntüsünü kullanarak**, önceden öğrendiği örüntülerden bakış yönü çıkarır. Bu, mevcut yönteme eklenen bir filtreye göre daha esaslı bir değişiklik. Örneğin L2CS-Net’in hazır ağırlıkları ve kamera üzerinden çalışan uygulaması mevcut. Ancak çıktısı bakış yönüdür; bunu bizim ekrana eşleyen kişisel kalibrasyon yine gerekir. **Daha iyi çalışacağı garanti değil.** [L2CS-Net](https://github.com/Ahmednull/L2CS-Net)

Üstelik bu seçenek projede **#79 belgesinde önerilmiş, fakat uygulanmamış**. Yani elimizde henüz değerlendirilmemiş, teknik olarak farklı bir yol bulunuyor. [Mevcut değerlendirme](/Users/cagri/Desktop/fatih-yedek/eye-tracker/docs/research/appearance-gaze-options.md)

Ben geliştirmeyi şu sıraya koyardım:

1. **Tek kamerayla çalışan, hazır modele dayalı bir bakış motoru.** Önce görüntü → bakış yönü → ekran koordinatı zincirini tamamlarız. MacBook ve iPhone seçeneklerini koruruz; iki kamerayı birleştirmeyi, temel tahmin anlaşılır hâle geldikten sonra ele alırız.
2. **Tek, düzgün bir kullanım akışı.** Kamera yerleşimi, kalibrasyon, canlı kullanım ve takip kaybından dönüş aynı uygulamada olur. Her küçük değişiklik için yeni deney betiği açmayız.
3. **İlk somut ürün hedefi: gözle birkaç büyük düğmeyi güvenilir seçmek.** Sonra klavye ve daha küçük hedeflere ilerleriz. Büyük düğmelerin mevcut hatayı kendiliğinden çözeceğini varsayamayız; önceki kaba bölge deneyi de başarısızdı. Bu yüzden önce bakış motorunu değiştirmeyi öneriyorum.

Bir de bu yolun **çıkış kararı** olmalı: hazır görüntü tabanlı yaklaşım da normal oturuşta kullanılabilir kararlılık sağlayamazsa, standart kameralarla hassas kontrol hedefini yeniden ele alırız. O noktada özel göz takip donanımı veya etkileşim tasarımında değişiklik konuşulur; aynı kalibrasyon döngüsüne aylar daha devam edilmez.

**Şu anki kararım: yeni A/B testi hazırlamak yerine, hazır bir bakış modelini seçip çalışan uygulamanın temeline koymak.** Göz takibi hedefini koruyarak ilerlemek için en gerekçeli yeni yön bu.